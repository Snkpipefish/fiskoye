"""NVE Hydapi: målestasjoner og historisk vannføring (krever gratis nøkkel i NVE_HYDAPI_KEY)."""
from __future__ import annotations

import os
from collections import defaultdict

import requests

API = "https://hydapi.nve.no/api/v1"


def _key():
    return os.environ.get("NVE_HYDAPI_KEY")


def _headers():
    return {"X-API-Key": _key(), "Accept": "application/json"}


def find_stations(bbox, hints: list[str], params: dict, max_n: int = 4) -> list[dict]:
    if not _key():
        return []
    s_, w_, n_, e_ = bbox
    pad = 0.3
    r = requests.get(f"{API}/Stations", params={"Active": 1, "Parameter": params.get("q", 1001)}, headers=_headers(), timeout=60)
    r.raise_for_status()
    st = []
    for x in r.json().get("data", []):
        lat, lon = x.get("latitude") or 0, x.get("longitude") or 0
        if not (s_ - pad <= lat <= n_ + pad and w_ - pad <= lon <= e_ + pad):
            continue
        name = (x.get("stationName") or "")
        score = 2 if any(h.lower() in name.lower() for h in hints) else (1 if s_ <= lat <= n_ and w_ <= lon <= e_ else 0)
        if score:
            st.append({"stationId": x["stationId"], "name": name, "river": x.get("riverName"), "lat": lat, "lon": lon,
                       "url": f"https://sildre.nve.no/station/{x['stationId']}", "score": score})
    st.sort(key=lambda z: -z["score"])
    return st[:max_n]


def monthly_median_q(station_id: str, param: int = 1001, years: int = 10) -> list[float | None]:
    """Månedsmedian av døgnmiddel vannføring siste `years` år."""
    if not _key():
        return [None] * 12
    o = requests.get(f"{API}/Observations", params={"StationId": station_id, "Parameter": param, "ResolutionTime": "day",
                                                   "ReferenceTime": f"P{years}Y/"}, headers=_headers(), timeout=120).json()
    obs = (o.get("data") or [{}])[0].get("observations") or []
    by = defaultdict(list)
    for x in obs:
        if x.get("value") is not None:
            by[int(x["time"][5:7])].append(float(x["value"]))
    out = []
    for m in range(1, 13):
        v = sorted(by.get(m, []))
        out.append(round(v[len(v) // 2], 1) if v else None)
    return out
