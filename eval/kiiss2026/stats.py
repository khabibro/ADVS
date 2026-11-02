"""Exact binomial (Clopper-Pearson) bounds without SciPy: bisection on the binomial CDF."""

from __future__ import annotations

import math


def _log_pmf(i: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if i == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if i == n else -math.inf
    return math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log1p(-p)


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k), X ~ Binomial(n, p)."""
    if k >= n:
        return 1.0
    return min(1.0, sum(math.exp(_log_pmf(i, n, p)) for i in range(0, k + 1)))


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k)."""
    if k <= 0:
        return 1.0
    return min(1.0, sum(math.exp(_log_pmf(i, n, p)) for i in range(k, n + 1)))


def _bisect(f, lo: float = 0.0, hi: float = 1.0) -> float:
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def upper_one_sided(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound: the p with P(X <= k | p) = 1 - conf."""
    if n <= 0:
        return float("nan")
    if k >= n:
        return 1.0
    alpha = 1.0 - conf
    if k == 0:
        return 1.0 - alpha ** (1.0 / n)
    return _bisect(lambda p: binom_cdf(k, n, p) > alpha)


def lower_one_sided(k: int, n: int, conf: float = 0.95) -> float:
    if n <= 0:
        return float("nan")
    if k <= 0:
        return 0.0
    alpha = 1.0 - conf
    if k == n:
        return alpha ** (1.0 / n)
    return _bisect(lambda p: binom_sf(k, n, p) < alpha)


def two_sided(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Two-sided Clopper-Pearson interval (each tail (1-conf)/2)."""
    if n <= 0:
        return (float("nan"), float("nan"))
    tail = (1.0 - conf) / 2.0
    lo = 0.0 if k == 0 else lower_one_sided(k, n, 1.0 - tail)
    hi = 1.0 if k == n else upper_one_sided(k, n, 1.0 - tail)
    return lo, hi


def rule_of_three(n: int) -> float:
    return 3.0 / n if n > 0 else float("nan")


if __name__ == "__main__":
    # sanity checks against closed forms / well-known values
    assert abs(upper_one_sided(0, 1523) - (1 - 0.05 ** (1 / 1523))) < 1e-12
    assert abs(upper_one_sided(0, 14) - 0.1926) < 1e-3
    assert abs(upper_one_sided(1, 1523) - 0.003) < 5e-4          # ~ 0.00311
    lo, hi = two_sided(1, 10)
    assert abs(lo - 0.0025) < 1e-3 and abs(hi - 0.4450) < 1e-3     # known exact 95% CI for 1/10
    lo, hi = two_sided(5, 20)
    assert abs(lo - 0.0866) < 1e-3 and abs(hi - 0.4910) < 1e-3
    print("stats self-check OK", round(upper_one_sided(1, 1523), 5), round(upper_one_sided(0, 1523), 5))
