import math

from fiskpipe.suitability import gauss_asym, linear, noisy_or, trapezoid, wgeomean


def test_trapezoid_endpoints():
    assert trapezoid(0.3, 0.3, 1, 3.5, 7) == 0
    assert trapezoid(7, 0.3, 1, 3.5, 7) == 0
    assert trapezoid(2, 0.3, 1, 3.5, 7) == 1
    assert abs(trapezoid(0.65, 0.3, 1, 3.5, 7) - 0.5) < 1e-9
    assert abs(trapezoid(5.25, 0.3, 1, 3.5, 7) - 0.5) < 1e-9


def test_linear_and_reverse():
    assert linear(0.05, 0.05, 0.5) == 0
    assert linear(0.5, 0.05, 0.5) == 1
    assert linear(0.9, 0.05, 0.5) == 1
    assert linear(0.0, 0.5, 0.0) == 1      # fallende
    assert abs(linear(0.25, 0.5, 0.0) - 0.5) < 1e-9


def test_gauss_asym():
    assert gauss_asym(16, 16, 6, 4) == 1
    assert abs(gauss_asym(10, 16, 6, 4) - math.exp(-0.5)) < 1e-9
    assert gauss_asym(30, 16, 6, 4, lo=1, hi=26) == 0.05


def test_wgeomean_weights():
    assert abs(wgeomean([1, 1, 1], [0.5, 0.3, 0.2]) - 1) < 1e-9
    assert abs(wgeomean([0.5, 0.5], [1, 1]) - 0.5) < 1e-9
    assert wgeomean([0, 1], [0.5, 0.5]) > 0   # gulv
    assert wgeomean([1], [0]) == 0


def test_noisy_or_bounds():
    assert noisy_or([]) == 0
    assert abs(noisy_or([(1, 1)]) - 1) < 1e-9
    v = noisy_or([(0.5, 1), (0.5, 1)])
    assert abs(v - 0.75) < 1e-9
