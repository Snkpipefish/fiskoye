"""Genererer fixtures/bite_ref.json (fasit for JS-paritet) og sjekker sunne egenskaper."""
import json
from pathlib import Path

import yaml

from tests import bite_ref as B

CFG = Path(__file__).resolve().parent.parent / "config" / "species.yaml"
FIX = Path(__file__).resolve().parent / "fixtures" / "bite_ref.json"

CASES = [
    {"navn": "gjedde-okt-skumring", "art": "gjedde", "ctx": {"doy": 280, "hour": 18.5, "sunrise": 7.3, "sunset": 18.6, "sun_alt": -1, "tw": 11, "dp3": -2, "wind": 3, "cloud": 80, "a": -0.1, "turb": 0.1}},
    {"navn": "gjedde-okt-middag", "art": "gjedde", "ctx": {"doy": 280, "hour": 13.0, "sunrise": 7.3, "sunset": 18.6, "sun_alt": 25, "tw": 11, "dp3": 0, "wind": 3, "cloud": 10, "a": -0.1, "turb": 0.1}},
    {"navn": "abbor-juli-kveld", "art": "abbor", "ctx": {"doy": 200, "hour": 21.0, "sunrise": 4.3, "sunset": 22.2, "sun_alt": 5, "tw": 19, "dp3": 0.5, "wind": 2, "cloud": 30, "a": None, "turb": 0.0}},
    {"navn": "lake-jan-natt", "art": "lake", "ctx": {"doy": 20, "hour": 23.0, "sunrise": 9.0, "sunset": 15.8, "sun_alt": -30, "tw": 1, "dp3": -1.5, "wind": 5, "cloud": 100, "a": 0.2, "turb": 0.0}},
    {"navn": "orret-juni-flom", "art": "orret", "ctx": {"doy": 165, "hour": 10.0, "sunrise": 3.9, "sunset": 22.6, "sun_alt": 45, "tw": 13, "dp3": 6, "wind": 12, "cloud": 0, "a": 0.9, "turb": 0.8}},
]


def load():
    return yaml.safe_load(CFG.read_text(encoding="utf-8"))["species"]


def test_write_fixture_and_sanity():
    sp = load()
    out = []
    for c in CASES:
        A, comps = B.activity(sp[c["art"]], c["ctx"])
        out.append({**c, "A": A, "comps": comps})
    FIX.parent.mkdir(exist_ok=True)
    FIX.write_text(json.dumps({"W": B.W, "cases": out}, indent=1), encoding="utf-8")
    by = {o["navn"]: o for o in out}
    assert by["gjedde-okt-skumring"]["A"] > by["gjedde-okt-middag"]["A"]
    assert by["lake-jan-natt"]["comps"]["diel"] == 1.0
    assert by["abbor-juli-kveld"]["comps"]["sesong"] >= 0.95
    assert by["orret-juni-flom"]["comps"]["flow"] < 0.4 and by["orret-juni-flom"]["comps"]["trykk"] == 0.6
    assert 0 < by["gjedde-okt-skumring"]["A"] <= 1


def test_season_wrap():
    m = [1] + [0] * 11
    assert B.f_sesong(m, 15) > 0.99
    assert B.f_sesong(m, 365) > 0.4
