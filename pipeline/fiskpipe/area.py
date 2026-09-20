"""Orkestrering per område: fetch -> kanal -> fjernmåling -> struktur -> score -> spots -> eksport."""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone

import numpy as np
import yaml
from pyproj import Transformer
from rasterio.warp import transform_bounds

from . import channel, export, features, hydraulics, network, remote, scoring, spots
from .paths import CONFIG_DIR, DATA_DIR
from .sources import esri, gbif, kartverket, nve, openmeteo, osm, sentinel


def load_config():
    areas = yaml.safe_load((CONFIG_DIR / "areas.yaml").read_text(encoding="utf-8"))["areas"]
    species = yaml.safe_load((CONFIG_DIR / "species.yaml").read_text(encoding="utf-8"))["species"]
    return areas, species


def _merge_rules(base: dict, over: dict | None) -> dict:
    out = dict(base or {})
    for k, v in (over or {}).items():
        out[k] = v
    return out


def run_area(slug: str, skip_sentinel=False, skip_images=False, skip_gbif=False) -> dict:
    t0 = time.time()
    areas, species_all = load_config()
    cfg = areas[slug]
    bbox = cfg["bbox"]
    pad = 0.02
    buf = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad]
    epsg = cfg.get("utm_epsg", 25833)
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    inv = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    out = DATA_DIR / "areas" / slug
    out.mkdir(parents=True, exist_ok=True)
    main = cfg["waters"][0]

    print(f"[{slug}] OSM …", flush=True)
    ww = osm.waterways(buf)
    polys = osm.river_polygons(buf)
    bridges, dams, ramps = osm.bridges(buf), osm.dams(buf), osm.boat_ramps(buf)
    roads, places = osm.roads(buf), osm.named_places(buf)
    print(f"  {len(ww)} vassdragsveier, {len(polys)} elveflater, {len(bridges)} bruer, {len(dams)} dammer, {len(ramps)} utsett/brygger, {len(roads)} veier")

    net = network.build_network(ww, epsg)
    network.compute_upstream(net)
    chains = network.chain_named(net, main["osm_names"])
    if not chains:
        raise SystemExit(f"Fant ikke {main['name']} i OSM innenfor bbox")
    rs = network.clip_to_bbox(network.resample_chain(net, chains[0]), bbox)
    if rs is None:
        raise SystemExit("Hovedløpet ligger utenfor bbox")
    xy, ll = rs["xy"], rs["ll"]
    n = len(xy)
    print(f"  hovedløp {main['name']}: {n} segmenter à 100 m")

    print(f"[{slug}] DTM …", flush=True)
    bu = transform_bounds("EPSG:4326", f"EPSG:{epsg}", buf[1], buf[0], buf[3], buf[2])
    dtm, dtr = kartverket.fetch_dtm(bu)
    dtm = kartverket.fill_nan(dtm)
    z = kartverket.sample_dtm(dtm, dtr, xy[:, 0], xy[:, 1])
    zs = network.smooth_profile(z)
    S = network.slopes(zs)
    kappa = network.curvature(xy)
    nrm = channel.normals(xy)
    hs = kartverket.hillshade(dtm)

    # behold bare vannflater som berører hovedløpet (innsjøer og andre elver filtreres bort)
    from shapely.geometry import LineString
    chain_line = LineString(xy).buffer(40)
    polys_touch = []
    for p_ in polys:
        g = channel.river_polygon([p_], tr)
        if g is not None and g.intersects(chain_line):
            polys_touch.append(p_)
    print(f"  {len(polys_touch)} av {len(polys)} vannflater berører hovedløpet")
    poly = channel.river_polygon(polys_touch, tr)
    q_monthly = None
    stations = []
    try:
        stations = nve.find_stations(bbox, cfg.get("nve", {}).get("station_hints", []), cfg.get("nve", {}).get("params", {}))
        if stations:
            q_monthly = nve.monthly_median_q(stations[0]["stationId"], cfg.get("nve", {}).get("params", {}).get("q", 1001))
            stations[0]["q_monthly_median"] = q_monthly
            print(f"  NVE {stations[0]['name']}: månedsmedian {q_monthly}")
    except Exception as ex:  # noqa: BLE001
        print("  NVE feilet:", ex)
    q_ref = (q_monthly[7] if q_monthly and q_monthly[7] else None) or 0.8 * main.get("q_mean", 100)
    n_manning = main.get("manning_n", 0.035)

    segs = []
    w_l, w_r, npieces = np.zeros(n), np.zeros(n), np.zeros(n, int)
    for i in range(n):
        twd = channel.transect_width(poly, xy[i, 0], xy[i, 1], nrm[i, 0], nrm[i, 1])
        if twd is None:
            w_l[i] = w_r[i] = 1.5 * math.sqrt(q_ref); npieces[i] = 0
        else:
            w_l[i], w_r[i], npieces[i] = twd
    # glatt bredder lett (fjerner enkeltavvik), behold lokale forskjeller
    from scipy.ndimage import median_filter
    w_l, w_r = median_filter(w_l, 3), median_filter(w_r, 3)
    shp = channel.shape_features(w_l, w_r)
    for i in range(n):
        j = min(i + 1, n - 1)
        line = [(ll[i, 1], ll[i, 0]), (ll[j, 1], ll[j, 0])] if j != i else [(ll[i - 1, 1], ll[i - 1, 0]), (ll[i, 1], ll[i, 0])]
        w = float(w_l[i] + w_r[i])
        h = hydraulics.manning_depth(q_ref, w, float(S[i]), n_manning)
        v = hydraulics.velocity(q_ref, w, h)
        bl, br = channel.bank_points(xy[i, 0], xy[i, 1], nrm[i, 0], nrm[i, 1], w_l[i], w_r[i])
        bll = inv.transform(bl[0], bl[1]); brl = inv.transform(br[0], br[1])
        segs.append({"i": i, "km": float(rs["s"][i] / 1000), "x": float(xy[i, 0]), "y": float(xy[i, 1]), "lat": float(ll[i, 0]), "lon": float(ll[i, 1]),
                     "line": line, "z": float(zs[i]), "S": float(S[i]), "kappa": float(kappa[i]), "nx": float(nrm[i, 0]), "ny": float(nrm[i, 1]),
                     "w": w, "w_v": float(w_l[i]), "w_h": float(w_r[i]), "island": bool(npieces[i] >= 2),
                     "innsnevring": float(shp["innsnevring"][i]), "bukt_v": float(shp["bukt_v"][i]), "bukt_h": float(shp["bukt_h"][i]),
                     "h": h, "v": v, "klasse_strom": hydraulics.current_class(v), "Q": q_ref,
                     "bank_xy": {"v": bl, "h": br}, "bank_ll": {"v": (bll[1], bll[0]), "h": (brl[1], brl[0])},
                     "side_navn_v": channel.compass8(nrm[i, 0], nrm[i, 1]) + "-bredden", "side_navn_h": channel.compass8(-nrm[i, 0], -nrm[i, 1]) + "-bredden"})

    # bare strukturer nær hovedløpet (bruer over sidebekker og veier er støy)
    def _near(pts, maxd=180.0):
        if not pts:
            return []
        from scipy.spatial import cKDTree
        tree = cKDTree(xy)
        keep = []
        for p_ in pts:
            px, py = tr.transform(p_["lon"], p_["lat"])
            d_, _ = tree.query((px, py))
            if d_ <= maxd + (poly.distance(__import__("shapely.geometry", fromlist=["Point"]).Point(px, py)) if poly is not None else 0) * 0 and (poly is None or poly.distance(__import__("shapely.geometry", fromlist=["Point"]).Point(px, py)) <= maxd):
                keep.append(p_)
        return keep
    bridges, dams, ramps = _near(bridges), _near(dams, 400), _near(ramps, 250)
    print(f"  nær elva: {len(bridges)} bruer, {len(dams)} dammer, {len(ramps)} utsett/brygger")
    trib = network.tributary_mouths(net, set(chains[0]), xy, main["osm_names"])
    print(f"  sideelver/bekker: {[t['name'] for t in trib]}")
    features.structure_features(segs, trib, bridges, dams, ramps, tr)

    s2meta = None
    if not skip_sentinel:
        print(f"[{slug}] Sentinel-2 …", flush=True)
        comp = sentinel.composite(bbox)
        if comp:
            c, ctr, cshape, s2meta = comp
            remote.segment_stats(c, ctr, segs, inv)
            sentinel.rgb_png(c["rgb"], out / "s2_rgb.png")
            (out / "s2_rgb.json").write_text(json.dumps({"bounds": [[bbox[0], bbox[1]], [bbox[2], bbox[3]]], **s2meta}), encoding="utf-8")
        else:
            print("  ingen brukbare S2-scener")
    if s2meta is None:
        for s in segs:
            for k in ("stumpf_v", "stumpf_h", "stumpf_c", "veg_v", "veg_h", "sand_v", "sand_h", "tre_v", "tre_h"):
                s[k] = np.nan
            s["banktype_v"] = s["banktype_h"] = None
    remote.finalize_depth(segs)
    features.shade(segs, hs, dtr, kartverket.sample_dtm)

    # arter i området
    present_cfg = cfg.get("species_present", {})
    gb = {}
    if not skip_gbif:
        try:
            print(f"[{slug}] GBIF …", flush=True)
            key = gbif.class_key()
            reg = [bbox[0] - 0.5, bbox[1] - 0.5, bbox[2] + 0.5, bbox[3] + 0.5]
            gb = gbif.summarize(gbif.occurrences(bbox, key), gbif.occurrences(reg, key, max_pages=40))
            print("  GBIF:", {k: (v["n_area"], v["n_region"]) for k, v in gb.items()})
        except Exception as ex:  # noqa: BLE001
            print("  GBIF feilet:", ex)
    species = {}
    for sid, sp in species_all.items():
        pres = present_cfg.get(sid) or (gb.get(sid, {}).get("presence")) or "usikker"
        if pres in ("sikker", "mulig"):
            species[sid] = sp
    print(f"  arter: {list(species)}")

    scoring.score_all(species, segs)
    access = features.AccessIndex(roads, tr)
    sp_list = spots.build_spots(segs, species, places, access, main["name"], inv)
    print(f"  {len(sp_list)} spots")

    if not skip_images:
        print(f"[{slug}] satellittutsnitt …", flush=True)
        for c in sp_list[:12]:
            try:
                img, mpp = esri.crop(c["lat"], c["lon"], 17)
                esri.annotate(img, mpp, f"{c['id']} {c['navn']} · {c['side_navn']}").save(out / f"satcheck_{c['id']}.jpg", quality=82)
                c["satsjekk"] = f"satcheck_{c['id']}.jpg"
            except Exception as ex:  # noqa: BLE001
                print("  bilde feilet", c["id"], ex)

    climate = None
    try:
        climate = openmeteo.climatology(*cfg["weather_point"])
        (out / "climate.json").write_text(json.dumps(climate, ensure_ascii=False), encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        print("  klimatologi feilet:", ex)

    sp_meta = {}
    for sid in species:
        sp_meta[sid] = {"presence": present_cfg.get(sid) or gb.get(sid, {}).get("presence", "usikker"),
                        "record": (cfg.get("records") or {}).get(sid),
                        "regler": _merge_rules(species_all[sid].get("regler"), (cfg.get("rules_overrides") or {}).get(sid)),
                        "gbif": gb.get(sid)}
    meta = {"slug": slug, "name": cfg["name"], "region": cfg["region"], "bbox": bbox, "view": cfg.get("view", [[bbox[0], bbox[1]], [bbox[2], bbox[3]]]),
            "weather_point": cfg["weather_point"], "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stats": {"segmenter": n, "spots": len(sp_list), "elveflater_osm": len(polys), "s2_scener": len((s2meta or {}).get("scener", []))},
            "waters": [{"name": w["name"], "kind": w["kind"], "q_mean": w.get("q_mean"), "manning_n": w.get("manning_n")} for w in cfg["waters"]],
            "q_ref": q_ref, "nve": {"stations": stations, "q_monthly_median": q_monthly, "hints": cfg.get("nve", {})},
            "structures": cfg.get("structures", []) + [{"name": d.get("name") or "dam/terskel", "kind": d["kind"], "lat": d["lat"], "lon": d["lon"]} for d in dams]
                          + [{"name": b.get("name") or b["kind"], "kind": b["kind"], "lat": b["lat"], "lon": b["lon"]} for b in bridges]
                          + [{"name": r.get("name") or r["kind"], "kind": r["kind"], "lat": r["lat"], "lon": r["lon"]} for r in ramps],
            "sideelver": trib, "fiskekort": cfg.get("fiskekort", []), "species": sp_meta, "climate": climate,
            "s2": s2meta, "notes": cfg.get("notes", ""), "disclaimer": cfg.get("disclaimer", ""), "seconds": round(time.time() - t0)}
    export.segments_geojson(segs, out / "segments.geojson", main["name"])
    export.spots_geojson(sp_list, out / "spots.geojson")
    export.gpx(sp_list, species, out / "points.gpx")
    export.kml(sp_list, species, cfg["name"], out / "points.kml")
    export.area_json(meta, out / "area.json")
    export.species_json(species_all, DATA_DIR / "species.json")
    export.write_index()
    # topp 5 per art til loggen
    for sid in species:
        top = sorted(sp_list, key=lambda c: -c["H"][sid])[:5]
        print(f"  {species[sid]['navn']:10s}: " + ", ".join(f"{c['navn']} ({c['side_navn']}) {c['H'][sid]:.0f}" for c in top))
    print(f"[{slug}] ferdig på {meta['seconds']} s")
    return meta
