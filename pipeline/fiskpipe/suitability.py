"""Egnethetskurver 0..1. Speiles nøyaktig i web/src/model/curves.js (paritet testes)."""
from __future__ import annotations

import math


def clip(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def trapezoid(x: float, d0: float, d1: float, d2: float, d3: float) -> float:
    """0 ved d0, stiger til 1 ved d1, 1 til d2, faller til 0 ved d3."""
    if x <= d0 or x >= d3:
        return 0.0
    if x < d1:
        return (x - d0) / max(d1 - d0, 1e-9)
    if x <= d2:
        return 1.0
    return (d3 - x) / max(d3 - d2, 1e-9)


def linear(x: float, v0: float, v1: float) -> float:
    """0 ved v0 -> 1 ved v1 (klampet). v0 > v1 gir fallende kurve."""
    if v0 == v1:
        return 1.0
    return clip((x - v0) / (v1 - v0))


def categorical(cls: str, table: dict, default: float = 0.3) -> float:
    return float(table.get(cls, default))


def gauss_asym(x: float, opt: float, s_lo: float, s_hi: float, lo=None, hi=None, floor: float = 0.05) -> float:
    if lo is not None and x < lo:
        return floor
    if hi is not None and x > hi:
        return floor
    s = s_lo if x < opt else s_hi
    return math.exp(-0.5 * ((x - opt) / max(s, 1e-6)) ** 2)


def wgeomean(values, weights, floor: float = 0.02) -> float:
    """Vektet geometrisk middel: exp(Σ w·ln max(f, floor)) / Σ w."""
    tot = sum(weights)
    if tot <= 0:
        return 0.0
    return math.exp(sum(w * math.log(max(v, floor)) for v, w in zip(values, weights)) / tot)


def noisy_or(pairs) -> float:
    """1 − Π(1 − w·x): «minst én sterk struktur hjelper»."""
    p = 1.0
    for w, x in pairs:
        p *= 1 - clip(w * x)
    return 1 - p
