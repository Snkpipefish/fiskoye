"""Segmentstatistikk fra Sentinel-2-kompositt: dybdeproxy, vegetasjon, sand, trekroner på bredden."""
from __future__ import annotations

import numpy as np


def _sample(arr: np.ndarray, tr, lons, lats):
    cols = ((np.asarray(lons) - tr.c) / tr.a).astype(int)
    rows = ((np.asarray(lats) - tr.f) / tr.e).astype(int)
    ok = (rows >= 0) & (rows < arr.shape[0]) & (cols >= 0) & (cols < arr.shape[1])
    out = np.full(len(rows), np.nan, np.float32)
    out[ok] = arr[rows[ok], cols[ok]]
    return out


def _frac(v, cond):
    v = v[np.isfinite(v)]
    return float(np.mean(cond(v))) if v.size else np.nan


def segment_stats(comp: dict, tr, segs: list[dict], inv) -> None:
    """Fyller hvert segment med: stumpf_v/h/c, veg_v/h, sand_v/h, tre_v/h, banktype_v/h.
    inv: Transformer UTM->4326 (always_xy)."""
    stumpf, ndvi, ndwi, red = comp["stumpf"], comp["ndvi"], comp["ndwi"], comp["red"]
    for s in segs:
        x, y, nx, ny = s["x"], s["y"], s["nx"], s["ny"]
        for side, sign, wside in (("v", 1, s["w_v"]), ("h", -1, s["w_h"])):
            bx, by = x + sign * nx * wside, y + sign * ny * wside      # breddkant
            # vannsiden: 5..30 m innover fra bredden, langs 3 parallelle spor (±20 m langs elva)
            offs = np.array([5, 12, 20, 30])
            alongs = np.array([-20, 0, 20])
            tx, ty = -ny, nx   # retning langs elva
            px = np.concatenate([[bx - sign * nx * o + tx * a for o in offs] for a in alongs])
            py = np.concatenate([[by - sign * ny * o + ty * a for o in offs] for a in alongs])
            lon, lat = inv.transform(px, py)
            st = _sample(stumpf, tr, lon, lat)
            nv = _sample(ndvi, tr, lon, lat); nw = _sample(ndwi, tr, lon, lat); rd = _sample(red, tr, lon, lat)
            s[f"stumpf_{side}"] = float(np.nanmean(st)) if np.isfinite(st).any() else np.nan
            vegm = np.isfinite(nv) & np.isfinite(nw)
            s[f"veg_{side}"] = float(np.mean((nv[vegm] > 0.25) & (nw[vegm] > -0.25))) if vegm.any() else np.nan
            sandm = np.isfinite(rd) & np.isfinite(nw)
            s[f"sand_{side}"] = float(np.mean((rd[sandm] > 0.06) & (nw[sandm] < 0.25) & (nw[sandm] > -0.3))) if sandm.any() else np.nan
            # landsiden: 15 og 35 m utover
            lx = np.array([bx + sign * nx * o + tx * a for o in (15, 35) for a in alongs])
            ly = np.array([by + sign * ny * o + ty * a for o in (15, 35) for a in alongs])
            lon, lat = inv.transform(lx, ly)
            lv = _sample(ndvi, tr, lon, lat)
            tre = _frac(lv, lambda v: v > 0.65)   # dyrket mark i juli ligger ofte 0,5–0,65
            s[f"tre_{side}"] = tre
            mean_ndvi = float(np.nanmean(lv)) if np.isfinite(lv).any() else np.nan
            s[f"banktype_{side}"] = ("skog/kratt" if (tre if np.isfinite(tre) else 0) > 0.5 else "eng/dyrket" if (mean_ndvi if np.isfinite(mean_ndvi) else 0) > 0.3 else "åpen/bebygd")
        # midtre tredel
        w = s["w_v"] + s["w_h"]
        mids = np.linspace(-w / 6, w / 6, 3)
        cx = np.array([x + nx * m + (-ny) * a for m in mids for a in (-20, 0, 20)])
        cy = np.array([y + ny * m + nx * a for m in mids for a in (-20, 0, 20)])
        lon, lat = inv.transform(cx, cy)
        st = _sample(stumpf, tr, lon, lat)
        s["stumpf_c"] = float(np.nanmean(st)) if np.isfinite(st).any() else np.nan


def finalize_depth(segs: list[dict]) -> None:
    """Z-score av Stumpf-ratio over området -> depth_z (relativ), dropoff per side."""
    vals = np.array([v for s in segs for v in (s.get("stumpf_v"), s.get("stumpf_h"), s.get("stumpf_c")) if v is not None and np.isfinite(v)])
    if vals.size < 10:
        for s in segs:
            for k in ("depth_z_v", "depth_z_h", "depth_z_c", "dropoff_v", "dropoff_h"):
                s[k] = 0.0
            s["depth_idx"] = 0.5
        return
    med = float(np.median(vals)); mad = float(np.median(np.abs(vals - med)) * 1.4826) or float(np.std(vals)) or 1e-3
    z = lambda v: 0.0 if v is None or not np.isfinite(v) else float(np.clip((v - med) / mad, -3, 3))
    for s in segs:
        s["depth_z_v"], s["depth_z_h"], s["depth_z_c"] = z(s.get("stumpf_v")), z(s.get("stumpf_h")), z(s.get("stumpf_c"))
        s["dropoff_v"] = float(np.clip((s["depth_z_c"] - s["depth_z_v"]) / 1.5, 0, 1))
        s["dropoff_h"] = float(np.clip((s["depth_z_c"] - s["depth_z_h"]) / 1.5, 0, 1))
        s["depth_idx"] = float(np.clip(0.5 + 0.25 * s["depth_z_c"], 0, 1))
