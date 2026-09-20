"""GBIF/Artsdatabanken: fiskeobservasjoner (Actinopterygii) innenfor bbox – bekrefter artsforekomst."""
from __future__ import annotations

from collections import Counter, defaultdict

from ..cache import cached_json

API = "https://api.gbif.org/v1"
# Latinsk navn -> fiskpipe-art-id
LATIN = {"Esox lucius": "gjedde", "Perca fluviatilis": "abbor", "Salmo trutta": "orret", "Thymallus thymallus": "harr",
         "Coregonus lavaretus": "sik", "Lota lota": "lake", "Rutilus rutilus": "mort", "Abramis brama": "brasme",
         "Leuciscus idus": "vederbuk", "Sander lucioperca": "gjors"}


def class_key(name="Actinopterygii") -> int | None:
    d = cached_json(f"{API}/species/match", {"name": name, "rank": "CLASS"}, subdir="gbif")
    return d.get("usageKey") or d.get("classKey")


def occurrences(bbox, key: int, max_pages: int = 20) -> list[dict]:
    s, w, n, e = bbox
    poly = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
    out = []
    off = 0
    while off < max_pages * 300:
        r = cached_json(f"{API}/occurrence/search", {"classKey": key, "geometry": poly, "hasCoordinate": "true", "limit": 300, "offset": off}, subdir="gbif")
        out += [{"species": o.get("species"), "lat": o.get("decimalLatitude"), "lon": o.get("decimalLongitude"),
                 "year": o.get("year"), "month": o.get("month")} for o in r.get("results", [])]
        if r.get("endOfRecords", True):
            break
        off += 300
    return out


def summarize(local: list[dict], regional: list[dict]) -> dict:
    """Per art: antall lokalt/regionalt, måneder (lokalt+regionalt) og presence-status."""
    res = {}
    loc = Counter(LATIN.get(o["species"]) for o in local if o.get("species") in LATIN)
    reg = Counter(LATIN.get(o["species"]) for o in regional if o.get("species") in LATIN)
    months = defaultdict(Counter)
    for o in local + regional:
        sid = LATIN.get(o.get("species"))
        if sid and o.get("month"):
            months[sid][int(o["month"])] += 1
    for sid in LATIN.values():
        n_l, n_r = loc.get(sid, 0), reg.get(sid, 0)
        res[sid] = {"n_area": n_l, "n_region": n_r, "months": [months[sid].get(m, 0) for m in range(1, 13)],
                    "presence": "sikker" if n_l >= 3 else "mulig" if n_r >= 3 else "usikker"}
    return res
