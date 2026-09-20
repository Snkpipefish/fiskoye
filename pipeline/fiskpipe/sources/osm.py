"""OpenStreetMap via Overpass: elver, elvepolygoner, bruer, dammer, båtutsett, veier, stedsnavn."""
from __future__ import annotations

from ..cache import cached_json

OVERPASS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter", "https://lz4.overpass-api.de/api/interpreter"]


def _query(q: str):
    import time
    last = None
    for host in OVERPASS:
        try:
            r = cached_json(host, data={"data": q}, timeout=240, retries=1, subdir="osm", min_bytes=50)
            if "remark" in r and "error" in str(r.get("remark", "")).lower():
                raise RuntimeError(f"Overpass-feil: {r['remark'][:120]}")
            time.sleep(1.5)   # vær snill med speilene
            return r
        except RuntimeError as e:
            last = e
            print("   overpass-speil feilet:", host.split("/")[2], str(e)[:80].replace("\n", " "))
    raise last


def _bbox_str(bbox):
    s, w, n, e = bbox
    return f"({s},{w},{n},{e})"


def _center(e):
    if e.get("type") == "node" and "lat" in e:
        return e["lat"], e["lon"]
    if "center" in e:
        return e["center"]["lat"], e["center"]["lon"]
    g = e.get("geometry")
    if g:
        return sum(p["lat"] for p in g) / len(g), sum(p["lon"] for p in g) / len(g)
    return None


def waterways(bbox) -> list[dict]:
    """Alle waterway=river|stream som linjer (for nettverkstopologi og sideelver)."""
    q = f'[out:json][timeout:180];(way["waterway"~"^(river|stream)$"]{_bbox_str(bbox)};);out tags geom;'
    return [e for e in _query(q)["elements"] if e.get("type") == "way" and "geometry" in e]


def river_polygons(bbox) -> list[dict]:
    """Elveflater: natural=water + water=river|canal (veier og multipolygon-relasjoner) samt waterway=riverbank.
    Geometrien klippes til bbox med out geom(bbox) – Glomma-relasjonene er ellers enorme.
    Returnerer liste av {"outer": [[(lon,lat)...]], "inner": [[...]], "tags": {...}}."""
    b = _bbox_str(bbox)
    s, w, n, e = bbox
    q = (f'[out:json][timeout:240];(way["natural"="water"]["water"~"^(river|canal)$"]{b};way["waterway"="riverbank"]{b};'
         f'relation["natural"="water"]["water"~"^(river|canal)$"]{b};relation["waterway"="riverbank"]{b};);out geom({s},{w},{n},{e});')
    out = []
    for e_ in _query(q)["elements"]:
        if e_.get("type") == "way" and e_.get("geometry"):
            out.append({"outer": [[(p["lon"], p["lat"]) for p in e_["geometry"] if p]], "inner": [], "tags": e_.get("tags", {})})
        elif e_.get("type") == "relation":
            rings = {"outer": [], "inner": []}
            for m in e_.get("members", []):
                if m.get("type") != "way" or not m.get("geometry"):
                    continue
                role = "inner" if m.get("role") == "inner" else "outer"
                rings[role].append([(p["lon"], p["lat"]) for p in m["geometry"] if p])
            if rings["outer"]:
                out.append({"outer": rings["outer"], "inner": rings["inner"], "tags": e_.get("tags", {})})
    return out


def lakes(bbox) -> list[dict]:
    q = f'[out:json][timeout:180];(way["natural"="water"]["water"!~"^(river|canal|stream)$"]{_bbox_str(bbox)};);out tags geom;'
    return [e for e in _query(q)["elements"] if e.get("type") == "way" and "geometry" in e]


def bridges(bbox) -> list[dict]:
    b = _bbox_str(bbox)
    q = f'[out:json][timeout:120];(way["bridge"="yes"]["highway"]{b};way["bridge"="yes"]["railway"]{b};way["man_made"="bridge"]{b};);out tags center;'
    out = []
    for e in _query(q)["elements"]:
        c = _center(e)
        if c:
            t = e.get("tags", {})
            out.append({"lat": c[0], "lon": c[1], "name": t.get("name", ""), "kind": "jernbanebru" if t.get("railway") else "bru"})
    return out


def dams(bbox) -> list[dict]:
    b = _bbox_str(bbox)
    q = f'[out:json][timeout:120];(way["waterway"="dam"]{b};node["waterway"="dam"]{b};way["waterway"="weir"]{b};node["waterway"="weir"]{b};);out tags center;'
    out = []
    for e in _query(q)["elements"]:
        c = _center(e)
        if c:
            t = e.get("tags", {})
            out.append({"lat": c[0], "lon": c[1], "name": t.get("name", ""), "kind": t.get("waterway", "dam")})
    return out


def boat_ramps(bbox) -> list[dict]:
    b = _bbox_str(bbox)
    q = (f'[out:json][timeout:120];(node["leisure"="slipway"]{b};way["leisure"="slipway"]{b};node["man_made"="pier"]{b};way["man_made"="pier"]{b};'
         f'node["leisure"="fishing"]{b};way["leisure"="fishing"]{b};node["leisure"="marina"]{b};way["leisure"="marina"]{b};);out tags center;')
    out = []
    for e in _query(q)["elements"]:
        c = _center(e)
        if c:
            t = e.get("tags", {})
            out.append({"lat": c[0], "lon": c[1], "name": t.get("name", ""), "kind": t.get("leisure") or t.get("man_made")})
    return out


def named_places(bbox) -> list[dict]:
    b = _bbox_str(bbox)
    q = (f'[out:json][timeout:180];(node["name"]["place"]{b};node["name"]["natural"]{b};'
         f'way["name"]["natural"~"^(water|bay|strait|wetland|beach|cliff|valley|gorge|peak|sand)$"]{b};'
         f'node["name"]["waterway"]{b};way["name"]["landuse"="farmland"]{b};way["name"]["leisure"]{b};);out center;')
    out = []
    for e in _query(q)["elements"]:
        t = e.get("tags", {})
        c = _center(e)
        if c and t.get("name"):
            out.append({"name": t["name"], "lat": c[0], "lon": c[1], "kind": t.get("place") or t.get("natural") or t.get("waterway") or t.get("landuse") or t.get("leisure")})
    return out


def roads(bbox) -> list[dict]:
    """Kjørbare veier, traktorveier/stier og parkeringsplasser for adkomstvurdering."""
    b = _bbox_str(bbox)
    q = (f'[out:json][timeout:180];(way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|track|path|footway|bridleway)$"]{b};'
         f'node["amenity"="parking"]{b};way["amenity"="parking"]{b};);out tags geom;')
    out = []
    for e in _query(q)["elements"]:
        t = e.get("tags", {})
        if e.get("type") == "way" and "geometry" in e and t.get("highway"):
            out.append({"kind": "road" if t["highway"] not in ("path", "footway", "bridleway") else "path",
                        "highway": t["highway"], "name": t.get("name", ""), "geometry": e["geometry"]})
        elif t.get("amenity") == "parking":
            c = _center(e)
            if c:
                out.append({"kind": "parking", "lat": c[0], "lon": c[1], "name": t.get("name", "")})
    return out
