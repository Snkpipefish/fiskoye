"""Kanalgeometri fra OSM-elvepolygon: bredde per side, breddpunkter, innsnevring, bukter, øyer."""
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union


def river_polygon(polys: list[dict], tr) -> MultiPolygon | Polygon | None:
    """Union av OSM-elveflater i UTM. polys: [{"outer": [[(lon,lat)..]], "inner": [[..]]}]."""
    geoms = []
    for p in polys:
        for ring in p["outer"]:
            if len(ring) < 4:
                continue
            xs, ys = tr.transform([q[0] for q in ring], [q[1] for q in ring])
            holes = []
            for h in p["inner"]:
                if len(h) >= 4:
                    hx, hy = tr.transform([q[0] for q in h], [q[1] for q in h])
                    holes.append(list(zip(hx, hy)))
            try:
                g = Polygon(list(zip(xs, ys)), holes)
                if not g.is_valid:
                    g = g.buffer(0)
                if g.area > 100:
                    geoms.append(g)
            except Exception:  # noqa: BLE001
                continue
    if not geoms:
        return None
    return unary_union(geoms)


def normals(xy: np.ndarray) -> np.ndarray:
    """Enhetsnormal per punkt: venstre side sett nedstrøms (rotasjon +90°)."""
    d = np.gradient(xy, axis=0)
    n = np.hypot(d[:, 0], d[:, 1]); n[n == 0] = 1
    return np.column_stack([-d[:, 1] / n, d[:, 0] / n])


def transect_width(poly, x: float, y: float, nx: float, ny: float, half: float = 500.0):
    """Skjærer en tverrlinje med elvepolygonet. Returnerer (w_left, w_right, n_pieces) eller None."""
    if poly is None:
        return None
    line = LineString([(x - nx * half, y - ny * half), (x + nx * half, y + ny * half)])
    inter = poly.intersection(line)
    if inter.is_empty:
        return None
    pieces = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]
    if not pieces:
        return None
    c = Point(x, y)
    pieces.sort(key=lambda g: g.distance(c))
    seg = pieces[0]
    if seg.distance(c) > 60:      # senterlinja ligger langt utenfor flata
        return None
    (ax, ay), (bx, by) = seg.coords[0], seg.coords[-1]
    # projiser endepunktene på normalen
    ta = (ax - x) * nx + (ay - y) * ny
    tb = (bx - x) * nx + (by - y) * ny
    left, right = max(ta, tb), -min(ta, tb)
    return max(left, 1.0), max(right, 1.0), len(pieces)


def bank_points(x, y, nx, ny, w_left, w_right, inset: float = 3.0):
    """Punkter 3 m innenfor hver bredd (i vannet)."""
    return (x + nx * (w_left - inset), y + ny * (w_left - inset)), (x - nx * (w_right - inset), y - ny * (w_right - inset))


def rolling_median(a: np.ndarray, half: int = 10) -> np.ndarray:
    out = np.empty_like(a, dtype=float)
    for i in range(len(a)):
        out[i] = np.nanmedian(a[max(0, i - half): i + half + 1])
    return out


def shape_features(w_left: np.ndarray, w_right: np.ndarray, half: int = 10) -> dict:
    """innsnevring (0..1), bukt per side (0..1) fra lokal bredde vs løpende median."""
    w = w_left + w_right
    med = rolling_median(w, half)
    med_l = rolling_median(w_left, half); med_r = rolling_median(w_right, half)
    narrowing = np.clip((med - w) / np.maximum(med, 1e-6), 0, 1)
    bay_l = np.clip((w_left - med_l) / np.maximum(med_l, 1e-6), 0, 1)
    bay_r = np.clip((w_right - med_r) / np.maximum(med_r, 1e-6), 0, 1)
    return {"innsnevring": narrowing, "bukt_v": bay_l, "bukt_h": bay_r}


def compass8(nx: float, ny: float) -> str:
    """Retning (kompass) for en vektor i UTM (x øst, y nord)."""
    deg = (np.degrees(np.arctan2(nx, ny)) + 360) % 360
    return ["N", "NØ", "Ø", "SØ", "S", "SV", "V", "NV"][int(round(deg / 45)) % 8]
