"""Kanalhydraulikk: Manning-dybde, hastighet, strømklasse. Rene funksjoner (testet)."""
from __future__ import annotations

import math

CLASSES = (("stille", 0.15), ("svak", 0.40), ("moderat", 0.80), ("stryk", math.inf))


def manning_depth(q: float, w: float, s: float, n: float = 0.035) -> float:
    """Løser Q = (1/n)·w·h·R^(2/3)·S^(1/2), R = wh/(w+2h), for h (biseksjon)."""
    if q <= 0 or w <= 0 or s <= 0:
        return 0.0

    def f(h):
        r = w * h / (w + 2 * h)
        return (1 / n) * w * h * r ** (2 / 3) * math.sqrt(s) - q

    lo, hi = 1e-4, 1.0
    while f(hi) < 0 and hi < 1e4:
        hi *= 2
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def velocity(q: float, w: float, h: float) -> float:
    return q / max(w * h, 1e-6) if h > 0 else 0.0


def current_class(v: float) -> str:
    for name, upper in CLASSES:
        if v < upper:
            return name
    return "stryk"
