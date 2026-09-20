from fiskpipe.hydraulics import current_class, manning_depth, velocity


def test_manning_roundtrip():
    q, w, s, n = 400.0, 150.0, 1e-4, 0.035
    h = manning_depth(q, w, s, n)
    r = w * h / (w + 2 * h)
    q2 = (1 / n) * w * h * r ** (2 / 3) * s ** 0.5
    assert abs(q2 - q) / q < 1e-6
    assert 3.0 < h < 5.0            # bred, flat lavlandselv
    assert 0.5 < velocity(q, w, h) < 0.9


def test_classes():
    assert current_class(0.1) == "stille"
    assert current_class(0.3) == "svak"
    assert current_class(0.6) == "moderat"
    assert current_class(1.2) == "stryk"
    assert manning_depth(0, 10, 1e-3) == 0
