"""Open-Meteo arkiv (ERA5): klimatologi for lufttemp -> modellert vanntemp per måned."""
from __future__ import annotations

import math
from collections import defaultdict

from ..cache import cached_json

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def mohseni(ta: float, mu=0.5, alpha=24.0, beta=12.0, gamma=0.18) -> float:
    return mu + (alpha - mu) / (1 + math.exp(gamma * (beta - ta)))


def climatology(lat: float, lon: float, start="2010-01-01", end="2025-12-31") -> dict:
    d = cached_json(ARCHIVE, {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                              "daily": "temperature_2m_mean,precipitation_sum", "timezone": "Europe/Oslo"}, subdir="openmeteo", timeout=120)
    days = d["daily"]["time"]; t = d["daily"]["temperature_2m_mean"]; p = d["daily"]["precipitation_sum"]
    # EWMA av lufttemp med tidskonstant 7 døgn -> Mohseni
    tau = 7.0
    a = 1 - math.exp(-1 / tau)
    ta_s = None
    tm, tw, pm, cnt = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(int)
    for day, tt, pp in zip(days, t, p):
        if tt is None:
            continue
        ta_s = tt if ta_s is None else ta_s + a * (tt - ta_s)
        m = int(day[5:7])
        tm[m] += tt; tw[m] += mohseni(ta_s); pm[m] += (pp or 0); cnt[m] += 1
    return {"ta_month_mean": [round(tm[m] / max(cnt[m], 1), 1) for m in range(1, 13)],
            "tw_month_mean": [round(tw[m] / max(cnt[m], 1), 1) for m in range(1, 13)],
            "precip_month_mean_mm": [round(pm[m] / max(cnt[m] / 30.4, 1e-6), 0) for m in range(1, 13)],
            "kilde": "Open-Meteo ERA5-arkiv, vanntemp = Mohseni(EWMA_7d(lufttemp))"}
