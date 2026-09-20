#!/usr/bin/env python3
"""Henter live vannføring/vannstand/vanntemp fra NVE Hydapi for alle områder i config/areas.yaml.
Kjøres i GitHub Actions (cron) med NVE_HYDAPI_KEY som secret. Skriver web/public/data/live/nve.json.
Krever bare requests + pyyaml. Uten nøkkel skrives {"stations": {}} slik at siden fungerer likevel."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://hydapi.nve.no/api/v1"
ROOT = Path(__file__).resolve().parent.parent.parent


def load_areas():
    import yaml
    return yaml.safe_load((ROOT / "pipeline" / "config" / "areas.yaml").read_text(encoding="utf-8"))["areas"]


def obs(h, sid, param, res, ref):
    r = requests.get(f"{API}/Observations", params={"StationId": sid, "Parameter": param, "ResolutionTime": res, "ReferenceTime": ref}, headers=h, timeout=120)
    if r.status_code != 200:
        return []
    o = (r.json().get("data") or [{}])[0].get("observations") or []
    return [[x["time"], round(float(x["value"]), 2)] for x in o if x.get("value") is not None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "web" / "public" / "data" / "live" / "nve.json"))
    a = ap.parse_args()
    key = os.environ.get("NVE_HYDAPI_KEY")
    out = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "areas": {}}
    if not key:
        print("NVE_HYDAPI_KEY mangler – skriver tom fil", file=sys.stderr)
    else:
        h = {"X-API-Key": key, "Accept": "application/json"}
        allst = requests.get(f"{API}/Stations", params={"Active": 1}, headers=h, timeout=60).json().get("data", [])
        for slug, cfg in load_areas().items():
            s_, w_, n_, e_ = cfg["bbox"]
            hints = [x.lower() for x in cfg.get("nve", {}).get("station_hints", [])]
            params = cfg.get("nve", {}).get("params", {"q": 1001, "level": 1000, "tw": 1003})
            cands = []
            for x in allst:
                lat, lon = x.get("latitude") or 0, x.get("longitude") or 0
                if not (s_ - 0.3 <= lat <= n_ + 0.3 and w_ - 0.3 <= lon <= e_ + 0.3):
                    continue
                name = x.get("stationName") or ""
                score = 2 if any(hh in name.lower() for hh in hints) else 1 if (s_ <= lat <= n_ and w_ <= lon <= e_) else 0
                if score:
                    cands.append((score, x))
            cands.sort(key=lambda z: -z[0])
            stations = []
            for _, x in cands[:3]:
                sid = x["stationId"]
                q_day = obs(h, sid, params.get("q", 1001), "day", "P30D/")
                q_hour = obs(h, sid, params.get("q", 1001), "hour", "P2D/")
                lvl = obs(h, sid, params.get("level", 1000), "day", "P30D/")
                tw = obs(h, sid, params.get("tw", 1003), "day", "P14D/")
                # månedsmedian siste 10 år (for anomali)
                by = defaultdict(list)
                for t, v in obs(h, sid, params.get("q", 1001), "day", "P10Y/"):
                    by[int(t[5:7])].append(v)
                med = [round(sorted(by[m])[len(by[m]) // 2], 1) if by[m] else None for m in range(1, 13)]
                stations.append({"stationId": sid, "name": x.get("stationName"), "river": x.get("riverName"), "lat": x.get("latitude"), "lon": x.get("longitude"),
                                 "q_day": q_day, "q_hour": q_hour, "level_day": lvl, "tw_day": tw, "q_median_month": med,
                                 "url": f"https://sildre.nve.no/station/{sid}"})
                print(slug, sid, x.get("stationName"), "q siste:", q_day[-1] if q_day else None, file=sys.stderr)
            out["areas"][slug] = {"stations": stations}
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("skrev", p, file=sys.stderr)


if __name__ == "__main__":
    main()
