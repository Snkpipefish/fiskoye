"""Eksport: GeoJSON, GPX, KML, area.json, species.json, index.json."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .paths import DATA_DIR


def _r(v, n=2):
    if v is None:
        return None
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else round(float(v), n)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return _r(o, 3)


SEG_KEYS = ["i", "km", "w", "w_v", "w_h", "h", "v", "S", "klasse_strom", "depth_idx", "depth_z_v", "depth_z_h", "veg_v", "veg_h", "sand_v", "sand_h",
            "os", "os_navn", "sving", "innsnevring", "bukt_v", "bukt_h", "dropoff_v", "dropoff_h", "bru", "dam", "skygge_v", "skygge_h",
            "banktype_v", "banktype_h", "side_navn_v", "side_navn_h", "island"]


def segments_geojson(segs: list[dict], path: Path, river: str):
    feats = []
    for s in segs:
        props = {k: _r(s.get(k), 5 if k == "S" else 2) for k in SEG_KEYS}
        props["elv"] = river
        props["H"] = {sid: _r(max(v["v"], v["h"]), 0) for sid, v in s["H"].items()}
        props["Hs"] = {sid: [_r(v["v"], 0), _r(v["h"], 0)] for sid, v in s["H"].items()}
        props["bank"] = {"v": [round(s["bank_ll"]["v"][0], 5), round(s["bank_ll"]["v"][1], 5)], "h": [round(s["bank_ll"]["h"][0], 5), round(s["bank_ll"]["h"][1], 5)]}
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[round(x, 5), round(y, 5)] for x, y in s["line"]]}, "properties": props})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")


def spots_geojson(spots: list[dict], path: Path):
    feats = []
    for c in spots:
        props = _clean({k: v for k, v in c.items() if k not in ("lat", "lon", "x", "y")})
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]}, "properties": props})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")


def gpx(spots: list[dict], species: dict, path: Path, creator="fiskoye"):
    import xml.sax.saxutils as su
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', f'<gpx version="1.1" creator="{creator}" xmlns="http://www.topografix.com/GPX/1/1">']
    for c in spots:
        arts = ", ".join(f"{species[s]['navn']} {c['H'][s]:.0f}" for s in sorted(c["H"], key=lambda k: -c["H"][k])[:3])
        lines.append(f'  <wpt lat="{c["lat"]:.5f}" lon="{c["lon"]:.5f}"><name>{su.escape(f"{c["id"]} {c["navn"]} ({c["side_navn"]})")}</name>'
                     f'<desc>{su.escape(arts + ". " + c.get("adkomst", {}).get("adkomst", ""))}</desc></wpt>')
    lines.append("</gpx>")
    path.write_text("\n".join(lines), encoding="utf-8")


def kml(spots: list[dict], species: dict, area_name: str, path: Path):
    import xml.sax.saxutils as su
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>', f'<name>{su.escape("FISKEØYE – " + area_name)}</name>']
    for c in spots:
        arts = ", ".join(f"{species[s]['navn']} {c['H'][s]:.0f}" for s in sorted(c["H"], key=lambda k: -c["H"][k])[:3])
        lines.append(f'<Placemark><name>{su.escape(f"{c["id"]} {c["navn"]}")}</name><description>{su.escape(arts)}</description>'
                     f'<Point><coordinates>{c["lon"]:.5f},{c["lat"]:.5f},0</coordinates></Point></Placemark>')
    lines.append('</Document></kml>')
    path.write_text("\n".join(lines), encoding="utf-8")


def species_json(species: dict, path: Path):
    path.write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "species": species}, ensure_ascii=False, indent=0), encoding="utf-8")


def area_json(meta: dict, path: Path):
    path.write_text(json.dumps(_clean(meta), ensure_ascii=False, indent=0), encoding="utf-8")


def write_index():
    areas = []
    for p in sorted((DATA_DIR / "areas").glob("*/area.json")):
        a = json.loads(p.read_text(encoding="utf-8"))
        areas.append({"slug": a["slug"], "name": a["name"], "region": a["region"], "bbox": a["bbox"], "view": a["view"],
                      "n_spots": a["stats"]["spots"], "species": list(a["species"].keys()), "generated": a["generated"]})
    (DATA_DIR / "index.json").write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "areas": areas}, ensure_ascii=False, indent=1), encoding="utf-8")
    return areas
