"""Kanalgeometri fra OSM-elvepolygon: bredde per side, breddpunkter, innsnevring, bukter, øyer."""
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union


def river_polygon(polys: list[dict], tr, bbox_utm=None, chain_line=None):
    """Elveflate i UTM fra OSM-ringer. Ringene kan være klippet av Overpass (out geom(bbox)) og dermed åpne;
    derfor polygoniseres alle ringlinjer sammen med bbox-kanten, og flatene som berører senterlinja beholdes.
    polys: [{"outer": [[(lon,lat)..]], "inner": [[..]]}]."""
    from shapely.geometry import box
    from shapely.ops import polygonize
    from shapely.ops import linemerge
    raw = []
    B = box(*bbox_utm) if bbox_utm is not None else None
    for p in polys:
        for ring in p["outer"] + p["inner"]:
            if len(ring) < 2:
                continue
            xs, ys = tr.transform([q[0] for q in ring], [q[1] for q in ring])
            raw.append(LineString(list(zip(xs, ys))))
    if not raw:
        return None
    # multipolygon-ringer består av flere veier: sy dem sammen først
    merged_rings = linemerge(unary_union(raw))
    parts = [merged_rings] if merged_rings.geom_type == "LineString" else list(merged_rings.geoms)
    lines = []
    for l in parts:
        coords = list(l.coords)
        if B is not None and not l.is_ring:
            # fortsatt åpen (klippet av Overpass): forleng endepunktene til bbox-kanten slik at flaten lukkes
            for idx, pos in ((0, 0), (-1, len(coords))):
                pt = Point(coords[idx]); edge = B.exterior.interpolate(B.exterior.project(pt))
                coords.insert(pos, (edge.x, edge.y))
        lines.append(LineString(coords))
    if B is not None:
        lines.append(B.exterior)
    merged = unary_union(lines)
    faces = list(polygonize(merged))
    if chain_line is not None:
        # behold flater som inneholder punkter på senterlinja (landflatene rundt gjør ikke det)
        pts = [Point(c) for c in chain_line.coords]
        faces = [f for f in faces if sum(f.contains(pt) for pt in pts) >= 2]
    if bbox_utm is not None:
        faces = [f for f in faces if f.area < 0.5 * box(*bbox_utm).area]
    faces = [f for f in faces if f.area > 100]
    if not faces:
        return None
    return unary_union(faces)


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
