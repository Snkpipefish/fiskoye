"""Elvenett fra OSM + høyder fra DTM -> 100 m-punkter langs hovedløpet (fra gulløye, forenklet)."""
from __future__ import annotations

import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from pyproj import Transformer

SEG_LEN = 100.0


def _norm(name: str | None) -> str:
    n = unicodedata.normalize("NFKD", (name or "").strip().lower())
    return "".join(ch for ch in n if not unicodedata.combining(ch))


@dataclass
class Way:
    id: int
    name: str
    tags: dict
    xy: np.ndarray
    ll: np.ndarray
    node_keys: list
    length: float = 0.0
    L_up_start: float = 0.0


@dataclass
class Network:
    ways: dict
    out_edges: dict = field(default_factory=dict)
    in_edges: dict = field(default_factory=dict)
    L_up: dict = field(default_factory=dict)
    tr: Transformer | None = None


def build_network(osm_ways: list[dict], epsg: int) -> Network:
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    ways = {}
    for w in osm_ways:
        g = w["geometry"]
        if len(g) < 2:
            continue
        lon = np.array([p["lon"] for p in g]); lat = np.array([p["lat"] for p in g])
        x, y = tr.transform(lon, lat)
        nodes = w.get("nodes") or [(round(p["lat"], 7), round(p["lon"], 7)) for p in g]
        tags = w.get("tags", {})
        way = Way(id=w["id"], name=tags.get("name", ""), tags=tags, xy=np.column_stack([x, y]), ll=np.column_stack([lat, lon]), node_keys=list(nodes))
        way.length = float(np.sum(np.hypot(np.diff(x), np.diff(y))))
        ways[way.id] = way
    net = Network(ways=ways, tr=tr)
    out_e, in_e = defaultdict(list), defaultdict(list)
    for wid, w in ways.items():
        out_e[w.node_keys[0]].append(wid)
        in_e[w.node_keys[-1]].append(wid)
    net.out_edges, net.in_edges = out_e, in_e
    return net


def compute_upstream(net: Network) -> None:
    L_up: dict = {}
    ways, in_e = net.ways, net.in_edges

    def solve(node):
        stack = [(node, 0)]
        onpath = set()
        while stack:
            n, state = stack[-1]
            if n in L_up:
                stack.pop(); continue
            if state == 0:
                onpath.add(n); stack[-1] = (n, 1)
                for wid in in_e.get(n, []):
                    s = ways[wid].node_keys[0]
                    if s not in L_up and s not in onpath:
                        stack.append((s, 0))
            else:
                L_up[n] = sum(ways[wid].length + L_up.get(ways[wid].node_keys[0], 0.0) for wid in in_e.get(n, []))
                onpath.discard(n); stack.pop()

    for w in ways.values():
        for k in (w.node_keys[0], w.node_keys[-1]):
            if k not in L_up:
                solve(k)
    net.L_up = L_up
    for w in ways.values():
        w.L_up_start = L_up.get(w.node_keys[0], 0.0)


def chain_named(net: Network, names: list[str]) -> list[list[int]]:
    keys = {_norm(n) for n in names}
    sub = [w for w in net.ways.values() if _norm(w.name) in keys]
    if not sub:
        return []
    ids = {w.id for w in sub}
    succ = {w.id: [o for o in net.out_edges.get(w.node_keys[-1], []) if o in ids] for w in sub}
    pred = {w.id: [i for i in net.in_edges.get(w.node_keys[0], []) if i in ids] for w in sub}
    best: dict = {}

    def longest(wid, seen):
        if wid in best:
            return best[wid]
        seen.add(wid)
        cand = (net.ways[wid].length, [wid])
        for s in succ[wid]:
            if s in seen:
                continue
            l, path = longest(s, seen)
            if l + net.ways[wid].length > cand[0]:
                cand = (l + net.ways[wid].length, [wid] + path)
        best[wid] = cand
        return cand

    sys.setrecursionlimit(20000)
    chains, used = [], set()
    sources = [w.id for w in sub if not pred[w.id]] or [w.id for w in sub]
    sources.sort(key=lambda i: -net.ways[i].L_up_start)
    for s in sources:
        if s in used:
            continue
        _, path = longest(s, set())
        path = [p for p in path if p not in used]
        if path:
            used.update(path); chains.append(path)
    chains.sort(key=lambda c: -sum(net.ways[i].length for i in c))
    return chains


def resample_chain(net: Network, chain: list[int], step: float = SEG_LEN):
    pts = []
    for wid in chain:
        w = net.ways[wid]
        pts.append(w.xy if not pts else w.xy[1:] if np.allclose(w.xy[0], pts[-1][-1]) else w.xy)
    xy = np.vstack(pts)
    seg = np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < step:
        return None
    ss = np.arange(0, s[-1], step)
    xs = np.interp(ss, s, xy[:, 0]); ys = np.interp(ss, s, xy[:, 1])
    inv = Transformer.from_crs(net.tr.target_crs, "EPSG:4326", always_xy=True)
    lon, lat = inv.transform(xs, ys)
    return {"xy": np.column_stack([xs, ys]), "ll": np.column_stack([lat, lon]), "s": ss}


def clip_to_bbox(rs: dict, bbox) -> dict | None:
    s_, w_, n_, e_ = bbox
    ll = rs["ll"]
    inside = (ll[:, 0] >= s_) & (ll[:, 0] <= n_) & (ll[:, 1] >= w_) & (ll[:, 1] <= e_)
    if not inside.any():
        return None
    i0 = int(np.argmax(inside))
    after = np.where(~inside[i0:])[0]
    i1 = i0 + int(after[0]) if len(after) else len(ll)
    if i1 - i0 < 2:
        return None
    out = {k: v[i0:i1] for k, v in rs.items()}
    out["s"] = out["s"] - out["s"][0]
    return out


def smooth_profile(z: np.ndarray) -> np.ndarray:
    """Monotont ikke-økende nedstrøms (fjerner DTM-støy og bruer)."""
    return np.minimum.accumulate(z)


def slopes(z: np.ndarray, step: float = SEG_LEN, half: int = 5, floor: float = 2e-5) -> np.ndarray:
    n = len(z)
    out = np.empty(n)
    for i in range(n):
        a, b = max(0, i - half), min(n - 1, i + half)
        out[i] = (z[a] - z[b]) / max((b - a) * step, step)
    return np.maximum(out, floor)


def curvature(xy: np.ndarray, step: float = SEG_LEN, win: int = 2) -> np.ndarray:
    d = np.diff(xy, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    ang = np.concatenate([ang, ang[-1:]])
    n = len(ang)
    out = np.zeros(n)
    for i in range(n):
        a, b = max(0, i - win), min(n - 1, i + win)
        out[i] = abs(np.angle(np.exp(1j * (ang[b] - ang[a])))) / max((b - a) * step, step)
    return out


def tributary_mouths(net: Network, chain_ids: set, chain_xy: np.ndarray, main_names: list[str], min_up_m: float = 1500.0, max_d: float = 120.0) -> list[dict]:
    """Sideelver/bekker som munner ut i hovedløpet: sluttnoden ligger nær kjeden."""
    keys = {_norm(n) for n in main_names}
    out = []
    from scipy.spatial import cKDTree
    tree = cKDTree(chain_xy)
    for w in net.ways.values():
        if w.id in chain_ids or _norm(w.name) in keys:
            continue
        L = w.length + w.L_up_start
        if L < min_up_m and w.tags.get("waterway") != "river":
            continue
        d, i = tree.query(w.xy[-1])
        if d <= max_d:
            out.append({"name": w.name or ("sideelv" if w.tags.get("waterway") == "river" else "bekk"), "seg": int(i), "L_up_m": float(L), "lat": float(w.ll[-1, 0]), "lon": float(w.ll[-1, 1])})
    # dedupliser per segment (behold største)
    best = {}
    for t in out:
        if t["seg"] not in best or t["L_up_m"] > best[t["seg"]]["L_up_m"]:
            best[t["seg"]] = t
    return sorted(best.values(), key=lambda t: t["seg"])
