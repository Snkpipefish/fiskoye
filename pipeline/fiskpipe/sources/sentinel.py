"""Sentinel-2 L2A via Earth Search STAC (nøkkelfritt). Vannindekser: dybde-ratio, vegetasjon, sandbanke."""
from __future__ import annotations

import math

import numpy as np
import rasterio
import requests
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds, intersection

STAC = "https://earth-search.aws.element84.com/v1/search"
BANDS = ("blue", "green", "red", "nir", "scl")


def search(bbox, years=(2024, 2025, 2026), max_cloud=15, limit=40, months=("06-01", "09-30")) -> list[dict]:
    s, w, n, e = bbox
    items = []
    for y in years:
        body = {"collections": ["sentinel-2-l2a"], "bbox": [w, s, e, n],
                "datetime": f"{y}-{months[0]}T00:00:00Z/{y}-{months[1]}T23:59:59Z",
                "query": {"eo:cloud_cover": {"lt": max_cloud}}, "limit": limit}
        try:
            r = requests.post(STAC, json=body, timeout=90)
            r.raise_for_status()
            items += r.json().get("features", [])
        except requests.RequestException as ex:  # noqa: PERF203
            print("  STAC feilet", y, ex)
    items = [i for i in items if i["properties"].get("s2:nodata_pixel_percentage", 0) < 40]
    items.sort(key=lambda i: (i["properties"].get("eo:cloud_cover", 100)))
    return items


def grid(bbox, res_deg_lat=0.00009):
    """10 m-grid i EPSG:4326 for bbox. Returnerer (transform, (H, W))."""
    s, w, n, e = bbox
    res_lon = res_deg_lat / math.cos(math.radians((s + n) / 2))
    H = int(math.ceil((n - s) / res_deg_lat)); W = int(math.ceil((e - w) / res_lon))
    return from_origin(w, n, res_lon, res_deg_lat), (H, W)


def read_scene(item: dict, bbox, dst_transform, shape) -> dict[str, np.ndarray]:
    """Leser båndvinduer og reprojiserer til felles 4326-grid. Reflektans 0..1 (offset håndtert)."""
    out = {}
    props = item["properties"]
    baseline = str(props.get("s2:processing_baseline", "99.99"))
    offset_applied = props.get("earthsearch:boa_offset_applied", False)
    try:
        need_offset = (not offset_applied) and float(baseline) >= 4.0
    except ValueError:
        need_offset = not offset_applied
    for b in BANDS:
        href = item["assets"][b]["href"]
        with rasterio.open(href) as d:
            bnds = transform_bounds("EPSG:4326", d.crs, bbox[1], bbox[0], bbox[3], bbox[2])
            win = from_bounds(*bnds, d.transform).round_offsets().round_lengths()
            try:
                win = intersection(win, Window(0, 0, d.width, d.height))
            except Exception:  # noqa: BLE001
                return {}
            if win.width < 2 or win.height < 2:
                return {}
            arr = d.read(1, window=win).astype(np.float32)
            src_tr = d.window_transform(win)
            dst = np.full(shape, np.nan, np.float32)
            reproject(arr, dst, src_transform=src_tr, src_crs=d.crs, dst_transform=dst_transform, dst_crs="EPSG:4326",
                      resampling=Resampling.nearest if b == "scl" else Resampling.bilinear, src_nodata=0, dst_nodata=np.nan)
            if b != "scl":
                dst = (dst - 1000.0) / 10000.0 if need_offset else dst / 10000.0
                dst = np.where(np.isfinite(dst), np.clip(dst, 1e-4, 1.5), np.nan)
            out[b] = dst
    return out


def water_indices(sc: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """NDVI, NDWI, Stumpf-ratio (dybdeproxy: høyere = dypere/mørkere), rød reflektans, vannmaske."""
    B2, B3, B4, B8, scl = (sc[k] for k in ("blue", "green", "red", "nir", "scl"))
    ndvi = (B8 - B4) / np.maximum(B8 + B4, 1e-4)
    ndwi = (B3 - B8) / np.maximum(B3 + B8, 1e-4)
    cloudfree = ~np.isin(scl, [0, 1, 3, 8, 9, 10, 11])   # ikke sky/skygge/snø/nodata
    water = cloudfree & ((scl == 6) | (ndwi > 0.1))
    with np.errstate(divide="ignore", invalid="ignore"):
        stumpf = np.log(1000.0 * B2) / np.log(1000.0 * B3)
    return {"ndvi": np.where(cloudfree, ndvi, np.nan), "ndwi": np.where(cloudfree, ndwi, np.nan),
            "stumpf": np.where(water, stumpf, np.nan), "red": np.where(cloudfree, B4, np.nan),
            "water": water.astype(np.float32), "rgb": np.stack([B4, B3, B2], -1)}


def composite(bbox, max_scenes=3, years=(2024, 2025, 2026), max_cloud=15):
    """Median-kompositt av vannindekser over ≤max_scenes scener. Returnerer (dict, transform, shape, meta) eller None.
    Resultatet caches i pipeline/cache/s2/ (COG-lesing over nett tar mange minutter)."""
    import hashlib, json
    from pathlib import Path
    from ..paths import CACHE_DIR
    cdir = CACHE_DIR / "s2"; cdir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([bbox, max_scenes, years, max_cloud]).encode()).hexdigest()
    cpath = cdir / f"{key}.npz"
    if cpath.exists():
        z = np.load(cpath, allow_pickle=True)
        meta = json.loads(str(z["meta"]))
        tr, shape = grid(bbox)
        comp = {k: z[k] for k in ("ndvi", "ndwi", "stumpf", "red", "water", "rgb")}
        print("  S2 fra cache:", [s["datetime"] for s in meta["scener"]])
        return comp, tr, shape, meta
    res = _composite(bbox, max_scenes, years, max_cloud)
    if res:
        comp, tr, shape, meta = res
        np.savez_compressed(cpath, meta=json.dumps(meta), **{k: comp[k] for k in ("ndvi", "ndwi", "stumpf", "red", "water", "rgb")})
    return res


def _composite(bbox, max_scenes, years, max_cloud):
    items = search(bbox, years=years, max_cloud=max_cloud)
    tr, shape = grid(bbox)
    stacks: dict[str, list] = {"ndvi": [], "ndwi": [], "stumpf": [], "red": [], "water": [], "rgb": []}
    weights = []
    used = []
    per_tile: dict[str, int] = {}
    for it in items:
        tile = it["properties"].get("grid:code", "")
        if per_tile.get(tile, 0) >= 2:
            continue
        print("  S2", it["id"], it["properties"]["datetime"][:10], "sky", it["properties"].get("eo:cloud_cover"), flush=True)
        try:
            sc = read_scene(it, bbox, tr, shape)
        except Exception as ex:  # noqa: BLE001
            print("   lesefeil", ex)
            continue
        if not sc or np.isfinite(sc["red"]).mean() < 0.3:
            continue
        idx = water_indices(sc)
        for k in stacks:
            stacks[k].append(idx[k])
        month = int(it["properties"]["datetime"][5:7])
        weights.append(2.0 if month >= 8 else 1.0)   # sensommer: vegetasjon fullt utviklet
        used.append({"id": it["id"], "datetime": it["properties"]["datetime"][:10], "cloud": it["properties"].get("eo:cloud_cover")})
        per_tile[tile] = per_tile.get(tile, 0) + 1
        if len(used) >= max_scenes:
            break
    if not used:
        return None
    with np.errstate(all="ignore"):
        comp = {k: np.nanmedian(np.stack(v), axis=0) for k, v in stacks.items() if k != "rgb"}
        comp["rgb"] = np.nanmedian(np.stack(stacks["rgb"]), axis=0)
        # vektet NDVI (sensommer teller dobbelt)
        wsum = np.zeros(shape, np.float32); vsum = np.zeros(shape, np.float32)
        for a, wgt in zip(stacks["ndvi"], weights):
            ok = np.isfinite(a)
            vsum[ok] += a[ok] * wgt; wsum[ok] += wgt
        comp["ndvi"] = np.where(wsum > 0, vsum / np.maximum(wsum, 1e-6), np.nan)
    return comp, tr, shape, {"scener": used, "grid_res_deg": (tr.a, -tr.e)}


def rgb_png(rgb: np.ndarray, path):
    """Sann-farge PNG med 2–98 %-strekk per kanal."""
    from PIL import Image
    out = np.zeros(rgb.shape, np.uint8)
    for i in range(3):
        a = rgb[..., i]
        v = a[np.isfinite(a)]
        lo, hi = (np.percentile(v, 2), np.percentile(v, 98)) if v.size else (0, 1)
        out[..., i] = (np.clip((np.nan_to_num(a, nan=lo) - lo) / max(hi - lo, 1e-6), 0, 1) ** 0.9 * 255).astype(np.uint8)
    Image.fromarray(out, "RGB").save(path, optimize=True)
