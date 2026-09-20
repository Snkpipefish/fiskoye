"""Python-speil av web/src/model/bite.js sine komponentformler. Brukes til paritetstest (fixtures/bite_ref.json)."""
import math

from fiskpipe.suitability import gauss_asym, wgeomean

W = {"sesong": 0.2, "diel": 0.25, "temp": 0.2, "trykk": 0.1, "vind": 0.05, "lys": 0.05, "flow": 0.1, "klar": 0.05}


def f_sesong(maaned, doy, gyting=None):
    t = ((doy - 15.2) / 30.44) % 12
    i0 = int(math.floor(t)) % 12; i1 = (i0 + 1) % 12; fr = t - math.floor(t)
    v = maaned[i0] * (1 - fr) + maaned[i1] * fr
    if gyting:
        a = _doy(*gyting["fra"]); b = _doy(*gyting["til"])
        if (a <= doy <= b) if a <= b else (doy >= a or doy <= b):
            v *= gyting["effekt"]
    return v


def _doy(m, d):
    return sum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][: m - 1]) + d


def _cdiff(a, b):
    d = (a - b) % 24
    return d - 24 if d > 12 else d


def f_diel(h, sr, ss, sun_alt, diel):
    base = diel["dag"] if sun_alt > -6 else diel["natt"]
    s = diel["sigma_h"]
    g = lambda dx: math.exp(-dx * dx / (2 * s * s))
    return max(base, diel["daggry"] * g(_cdiff(h, sr + 0.5)), diel["skumring"] * g(_cdiff(h, ss - 0.5)))


def f_temp(tw, t):
    return gauss_asym(tw, t["opt"], t["sigma_lo"], t["sigma_hi"], t["min"], t["max"])


def f_trykk(dp3, tab):
    if abs(dp3) >= 4:
        k = "raskt"
    elif -4 < dp3 <= -1:
        k = "fallende"
    elif 1 <= dp3 < 4:
        k = "stigende"
    else:
        k = "stabil"
    return tab[k]


def f_vind(v, opt, mx):
    if v <= opt:
        return 1.0
    if v <= mx:
        return 1 - 0.6 * (v - opt) / (mx - opt)
    return 0.3


def f_lys(sun_alt, cloud, lys):
    if sun_alt <= 10:
        return 1.0
    c = cloud / 100
    return lys["sol"] * (1 - c) + lys["overskyet"] * c


def f_flow(a, a_opt, sigma):
    return 1.0 if a is None else math.exp(-((a - a_opt) ** 2) / (2 * sigma * sigma))


def f_klar(turb, fols):
    return 1 - fols * turb


def activity(sp, ctx):
    comps = {
        "sesong": f_sesong(sp["sesong"]["maaned"], ctx["doy"], sp["sesong"].get("gyting")),
        "diel": f_diel(ctx["hour"], ctx["sunrise"], ctx["sunset"], ctx["sun_alt"], sp["diel"]),
        "temp": f_temp(ctx["tw"], sp["habitat"]["temp_c"]),
        "trykk": f_trykk(ctx["dp3"], sp["vaer"]["trykk"]),
        "vind": f_vind(ctx["wind"], sp["vaer"]["vind"]["opt_ms"], sp["vaer"]["vind"]["max_ms"]),
        "lys": f_lys(ctx["sun_alt"], ctx["cloud"], sp["vaer"]["lys"]),
        "flow": f_flow(ctx.get("a"), sp["vaer"]["vannforing"]["a_opt"], sp["vaer"]["vannforing"]["sigma"]),
        "klar": f_klar(ctx["turb"], sp["vaer"]["klarhet"]["folsomhet"]),
    }
    keys = list(W)
    A = wgeomean([comps[k] for k in keys], [W[k] for k in keys])
    return A, comps
