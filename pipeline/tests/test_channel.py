import numpy as np
from shapely.geometry import Polygon

from fiskpipe.channel import bank_points, normals, shape_features, transect_width


def test_transect_width_rectangle():
    poly = Polygon([(0, -50), (1000, -50), (1000, 50), (0, 50)])   # 100 m bred elv langs x
    r = transect_width(poly, 500, 0, 0, 1)
    assert r is not None
    wl, wr, n = r
    assert abs(wl - 50) < 1e-6 and abs(wr - 50) < 1e-6 and n == 1
    assert transect_width(poly, 500, 500, 0, 1) is None          # langt utenfor


def test_bay_detection():
    wl = np.full(41, 60.0); wl[20] = 120.0
    wr = np.full(41, 60.0)
    f = shape_features(wl, wr)
    assert f["bukt_v"][20] > 0.9 and f["bukt_h"][20] == 0
    assert f["innsnevring"][20] == 0
    wl2 = np.full(41, 60.0); wl2[10] = 30.0
    f2 = shape_features(wl2, wr)
    assert f2["innsnevring"][10] > 0.2


def test_normals_and_banks():
    xy = np.array([[0, 0], [100, 0], [200, 0]], float)
    n = normals(xy)
    assert np.allclose(n[1], [0, 1])          # venstre = +y når vi går +x
    (lx, ly), (rx, ry) = bank_points(100, 0, 0, 1, 50, 50)
    assert (lx, ly) == (100, 47) and (rx, ry) == (100, -47)
