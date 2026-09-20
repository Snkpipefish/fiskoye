"""GBIF/Artsdatabanken: fiskeobservasjoner (Actinopterygii) innenfor bbox – bekrefter artsforekomst."""
from __future__ import annotations

from collections import Counter, defaultdict

from ..cache import cached_json

API = "https://api.gbif.org/v1"
# Latinsk navn -> fiskpipe-art-id
LATIN = {"Esox lucius": "gjedde", "Perca fluviatilis": "abbor", "Salmo trutta": "orret", "Thymallus thymallus": "harr",
         "Coregonus lavaretus": "sik", "Lota lota": "lake", "Rutilus rutilus": "mort", "Abramis brama": "brasme",
         "Leuciscus idus": "vederbuk", "Sander lucioperca": "gjors"}


def species_key(latin: str) -> int | None:
    d = cached_json(f"{API}/species/match", {"name": latin}, subdir="gbif")
    return d.get("usageKey") if d.get("matchType") in ("EXACT", "FUZZY") else None


def _poly(bbox):
    s, w, n, e = bbox
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


def counts(bbox, key: int) -> tuple[int, list[int]]:
    """Antall forekomster i bbox og månedsfordeling (facet), uten å laste ned enkeltposter."""
    r = cached_json(f"{API}/occurrence/search", {"taxonKey": key, "geometry": _poly(bbox), "hasCoordinate": "true", "limit": 0, "facet": "month", "facetLimit": 12}, subdir="gbif")
    months = [0] * 12
    for f in r.get("facets", []):
        if f.get("field") == "MONTH":
            for c in f.get("counts", []):
                m = int(c["name"]); months[m - 1] = int(c["count"])
    return int(r.get("count", 0)), months


def survey(bbox, regional_bbox) -> dict:
    """Per art: n_area, n_region, måneder (regionalt) og presence-status."""
    res = {}
    for latin, sid in LATIN.items():
        key = species_key(latin)
        if not key:
            res[sid] = {"n_area": 0, "n_region": 0, "months": [0] * 12, "presence": "usikker"}
            continue
        n_l, _ = counts(bbox, key)
        n_r, months = counts(regional_bbox, key)
        res[sid] = {"n_area": n_l, "n_region": n_r, "months": months, "presence": "sikker" if n_l >= 3 else "mulig" if n_r >= 3 else "usikker", "taxonKey": key}
    return res


def summarize_records(local: list[dict], regional: list[dict]) -> dict:
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
