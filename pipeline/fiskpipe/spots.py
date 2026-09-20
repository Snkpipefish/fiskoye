"""Velger fiskeplasser (spots) per art fra bredd-kandidater, klassifiserer A/B/C og lager statiske komponentlister."""
from __future__ import annotations

import math

import numpy as np

from .features import _hav


def pick_peaks(cands: list[dict], sid: str, n_max: int = 12, min_sep: float = 300.0) -> list[dict]:
    order = sorted(cands, key=lambda c: -c["H"][sid])
    chosen = []
    for c in order:
        if c["H"][sid] < 20:
            break
        if all(_hav(c["lat"], c["lon"], k["lat"], k["lon"]) >= min_sep for k in chosen):
            chosen.append(c)
        if len(chosen) >= n_max:
            break
    return chosen


def classify(h: float) -> str:
    return "A" if h >= 75 else "B" if h >= 50 else "C"


def nearest_place(lat, lon, places, maxd=500.0):
    best, bd = None, maxd
    for p in places:
        d = _hav(lat, lon, p["lat"], p["lon"])
        if d < bd:
            best, bd = p, d
    return best


def static_components(seg: dict, side: str) -> list[str]:
    """Nøkler som why.js oversetter til prosa."""
    out = []
    if seg[f"bukt_{side}"] > 0.35:
        out.append("bukt")
    if seg.get(f"dropoff_{side}", 0) > 0.4:
        out.append("dropoff")
    if seg["os"] > 0.5:
        out.append("os:" + (seg.get("os_navn") or "sideelv"))
    v = seg.get(f"veg_{side}") or 0
    if v > 0.4:
        out.append("veg_hoy")
    elif v > 0.15:
        out.append("veg")
    if seg["bru"] > 0.5:
        out.append("bru")
    if seg["dam"] > 0.4:
        out.append("dam:" + (seg.get("dam_navn") or "dam"))
    if seg["innsnevring"] > 0.3:
        out.append("innsnevring")
    if seg["sving"] > 0.4:
        out.append("sving")
    if (seg.get(f"sand_{side}") or 0) > 0.4:
        out.append("sandbanke")
    if seg["klasse_strom"] in ("moderat", "stryk"):
        out.append("strom:" + seg["klasse_strom"])
    if seg.get(f"skygge_{side}", 0) > 0.5:
        out.append("skygge")
    if seg.get("island"):
        out.append("oy")
    return out


def build_spots(segs: list[dict], species: dict, places: list[dict], access, river_name: str, tr_inv) -> list[dict]:
    cands = []
    for s in segs:
        for side in ("v", "h"):
            x, y = s["bank_xy"][side]
            lon, lat = tr_inv.transform(x, y)
            cands.append({"seg": s["i"], "side": side, "lat": float(lat), "lon": float(lon), "x": x, "y": y,
                          "H": {sid: s["H"][sid][side] for sid in species}, "_seg": s})
    chosen: dict[tuple, dict] = {}
    for sid in species:
        for rank, c in enumerate(pick_peaks(cands, sid), 1):
            key = (c["seg"], c["side"])
            sp = chosen.setdefault(key, {**{k: v for k, v in c.items() if k != "_seg"}, "rank": {}, "klasse": {}, "_seg": c["_seg"]})
            sp["rank"][sid] = rank
            sp["klasse"][sid] = classify(c["H"][sid])
    out = []
    for key, sp in chosen.items():
        s = sp.pop("_seg")
        side = sp["side"]
        p = nearest_place(sp["lat"], sp["lon"], places)
        sp["navn"] = f"{p['name']} · km {s['km']:.1f}" if p else f"{river_name} km {s['km']:.1f}"
        sp["side_navn"] = s[f"side_navn_{side}"]
        sp["elv"], sp["km"] = river_name, round(s["km"], 2)
        sp["komponenter"] = static_components(s, side)
        sp["adkomst"] = access.describe(sp["x"], sp["y"]) if access else {}
        sp["banktype"] = s.get(f"banktype_{side}")
        sp["dybde_est"] = round(s["komp"][next(iter(species))][side]["dybde_est"], 1)
        sp["veg"] = round(float(s.get(f"veg_{side}") or 0), 2)
        sp["skygge"] = round(float(s.get(f"skygge_{side}", 0)), 2)
        sp["klasse_strom"] = s["klasse_strom"]
        sp["w"], sp["h"], sp["v"] = round(s["w"], 0), round(s["h"], 1), round(s["v"], 2)
        sp["struct"] = {k: round(float(v), 2) for k, v in s["komp"][next(iter(species))][side]["struct"].items()}
        sp["f"] = {sid: {k: round(float(v), 3) for k, v in s["komp"][sid][side]["f"].items()} for sid in species}
        sp["beste_art"] = max(sp["H"], key=lambda k: sp["H"][k])
        sp["H_maks"] = round(max(sp["H"].values()), 0)
        out.append(sp)
    out.sort(key=lambda z: -z["H_maks"])
    for i, sp in enumerate(out, 1):
        sp["id"] = i
    return out
