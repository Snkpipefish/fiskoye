"""Statisk habitat-egnethet H_s per art, segment og bredd (0–100, normalisert per område)."""
from __future__ import annotations

import math

import numpy as np

from .suitability import categorical, gauss_asym, linear, noisy_or, trapezoid, wgeomean

STRUCT_KEYS = ("os", "sving", "innsnevring", "bukt", "dropoff", "bru", "dam", "sandbanke")


def depth_estimate(h_manning: float, depth_z: float) -> float:
    """Dybde (m) nær bredden: Manning-dybde skalert med relativ S2-dybde. Merket som estimat i UI."""
    return float(np.clip(h_manning * math.exp(0.35 * depth_z), 0.3, 12.0))


def components(sp: dict, seg: dict, side: str) -> dict:
    hab = sp["habitat"]
    dyb = depth_estimate(seg["h"], seg.get(f"depth_z_{side}", 0.0))
    veg = seg.get(f"veg_{side}"); veg = 0.0 if veg is None or not np.isfinite(veg) else veg
    sand = seg.get(f"sand_{side}"); sand = 0.0 if sand is None or not np.isfinite(sand) else sand
    struct = {"os": seg["os"], "sving": seg["sving"], "innsnevring": seg["innsnevring"], "bukt": seg[f"bukt_{side}"],
              "dropoff": seg.get(f"dropoff_{side}", 0.0), "bru": seg["bru"], "dam": seg["dam"], "sandbanke": sand}
    sw = hab["struktur"]
    f = {
        "dybde": trapezoid(dyb, *hab["dybde_m"]["trapes"]),
        "strom": categorical(seg["klasse_strom"], hab["strom"]),
        "vegetasjon": linear(veg, *hab["vegetasjon"]["lin"]),
        "struktur": noisy_or([(sw.get(k, 0.0), struct[k]) for k in STRUCT_KEYS]),
        "skygge": linear(seg.get(f"skygge_{side}", 0.0), *hab["skygge"]["lin"]),
    }
    return {"f": f, "dybde_est": dyb, "veg": veg, "sand": sand, "struct": struct}


def h_raw(sp: dict, seg: dict, side: str) -> tuple[float, dict]:
    c = components(sp, seg, side)
    vekt = sp["habitat"]["vekt"]
    keys = ("dybde", "strom", "vegetasjon", "struktur", "skygge")
    if seg.get("w", 0) < 5:
        return 0.0, c
    return wgeomean([c["f"][k] for k in keys], [vekt.get(k, 0.0) for k in keys]), c


def score_all(species: dict, segs: list[dict]) -> None:
    """Fyller seg["H"][art] = {"v": 0-100, "h": 0-100} og seg["komp"][art][side]."""
    for s in segs:
        s["H"], s["komp"] = {}, {}
    for sid, sp in species.items():
        raw = {}
        for i, s in enumerate(segs):
            for side in ("v", "h"):
                r, c = h_raw(sp, s, side)
                raw[(i, side)] = r
                s["komp"].setdefault(sid, {})[side] = c
        vals = np.array(list(raw.values()))
        p99 = float(np.percentile(vals, 99)) if vals.size else 1.0
        p99 = p99 if p99 > 1e-6 else 1.0
        for (i, side), r in raw.items():
            segs[i]["H"].setdefault(sid, {})[side] = float(np.clip(100.0 * r / p99, 0, 100))
