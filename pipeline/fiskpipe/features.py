"""Strukturtrekk per segment: os, sving, bru, dam, skygge, adkomst."""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree


def _hav(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _dist_to_points(segs, pts, tr):
    if not pts:
        return np.full(len(segs), np.inf), [None] * len(segs)
    xs, ys = tr.transform([p["lon"] for p in pts], [p["lat"] for p in pts])
    tree = cKDTree(np.column_stack([xs, ys]))
    d, i = tree.query(np.array([[s["x"], s["y"]] for s in segs]))
    return d, [pts[j] for j in i]


def structure_features(segs: list[dict], tributaries: list[dict], bridges: list[dict], dams: list[dict], ramps: list[dict], tr) -> None:
    n = len(segs)
    # os: avstand langs kjeden til nærmeste sideelv-munning (100 m per segment)
    for i, s in enumerate(segs):
        best, name = np.inf, None
        for t in tributaries:
            d = abs(i - t["seg"]) * 100.0
            if d < best:
                best, name = d, t["name"]
        s["os"] = float(math.exp(-best / 150.0)) if np.isfinite(best) else 0.0
        s["os_navn"] = name if s["os"] > 0.2 else None
        s["sving"] = float(np.clip(s["kappa"] * 200.0, 0, 1))
    d, near = _dist_to_points(segs, bridges, tr)
    for s, dd, b in zip(segs, d, near):
        s["bru"] = float(math.exp(-dd / 100.0)); s["bru_navn"] = (b or {}).get("name") if dd < 200 else None
    d, near = _dist_to_points(segs, dams, tr)
    for s, dd, b in zip(segs, d, near):
        s["dam"] = float(math.exp(-dd / 300.0)); s["dam_navn"] = (b or {}).get("name") if dd < 800 else None
    d, near = _dist_to_points(segs, ramps, tr)
    for s, dd, b in zip(segs, d, near):
        s["d_ramp_m"] = float(dd) if np.isfinite(dd) else None


def shade(segs: list[dict], hs: np.ndarray, transform, sample_fn) -> None:
    """skygge per side = 0,5·trekroner + 0,5·(1 − hillshade(SV, 25°)) ved breddpunktet."""
    for side in ("v", "h"):
        xs = np.array([s["bank_xy"][side][0] for s in segs]); ys = np.array([s["bank_xy"][side][1] for s in segs])
        h = sample_fn(hs, transform, xs, ys)
        for s, hh in zip(segs, h):
            tre = s.get(f"tre_{side}")
            tre = 0.0 if tre is None or not np.isfinite(tre) else tre
            s[f"skygge_{side}"] = float(np.clip(0.5 * tre + 0.5 * (1 - hh), 0, 1))


class AccessIndex:
    """Avstand til nærmeste bilvei, sti og parkering (m) for et punkt (fra gulløye)."""

    def __init__(self, roads: list[dict], tr):
        self.trees = {}
        for kind in ("road", "path", "parking"):
            pts, info = [], []
            for r in roads:
                if r["kind"] != kind:
                    continue
                if kind == "parking":
                    x, y = tr.transform(r["lon"], r["lat"]); pts.append((x, y)); info.append(r.get("name", ""))
                else:
                    g = r["geometry"]
                    xs, ys = tr.transform([p["lon"] for p in g], [p["lat"] for p in g])
                    for i in range(len(xs) - 1):
                        n = max(1, int(math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) // 25))
                        for k in range(n):
                            f = k / n; pts.append((xs[i] + f * (xs[i + 1] - xs[i]), ys[i] + f * (ys[i + 1] - ys[i])))
                            info.append(r.get("name") or r.get("highway", ""))
            self.trees[kind] = (cKDTree(np.array(pts)), info) if pts else None

    def describe(self, x: float, y: float) -> dict:
        out = {}
        for kind, key in (("road", "d_vei_m"), ("path", "d_sti_m"), ("parking", "d_parkering_m")):
            t = self.trees.get(kind)
            if t is None:
                out[key] = None; continue
            d, i = t[0].query((x, y))
            out[key] = round(float(d))
            if kind == "road":
                out["vei_navn"] = t[1][i]
        d = out.get("d_vei_m")
        if d is None:
            out["adkomst"] = "Ukjent adkomst (ingen veidata)."
        elif d < 150:
            out["adkomst"] = f"Lett: bilvei {d} m unna" + (f" ({out['vei_navn']})" if out.get("vei_navn") else "") + "."
        elif d < 600:
            out["adkomst"] = f"Kort gange: bilvei {d} m unna."
        elif d < 2000:
            out["adkomst"] = f"Gange {d / 1000:.1f} km fra nærmeste bilvei."
        else:
            out["adkomst"] = f"Avsides: {d / 1000:.1f} km fra bilvei."
        if out.get("d_parkering_m") is not None and out["d_parkering_m"] < 1500:
            out["adkomst"] += f" Parkering {out['d_parkering_m']} m unna."
        if out.get("d_sti_m") is not None and out["d_sti_m"] < 100:
            out["adkomst"] += " Sti langs vannet."
        return out
