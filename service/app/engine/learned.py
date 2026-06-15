"""The learned estimator — Phase 2: two-level signatures with category backoff.

It corrects a first-pass estimate toward observed actuals using a shrinkage
blend, but now prefers the *specific* bucket (this exact recurring item) once
it has enough samples, and falls back to the *category* average until then.

    corrected_total = estimate * k/(k+n) + observed_mean * n/(k+n)

n and observed_mean come from the chosen level. Confidence = n/(n+k) is the
weight given to observed data, so the number the UI shows is the number doing
the math. learn_level tells the UI which bucket taught it.
"""
from __future__ import annotations

from .base import Estimate, Estimator, Task
from .signature import signature
from ..store.actuals import ActualsStore

_PRIOR_WEIGHT = 3.0   # k: samples needed before observed data is trusted ~50/50
_MIN_SPECIFIC = 2     # specific samples needed before we stop falling back to category


class LearnedEstimator:
    def __init__(self, base: Estimator, store: ActualsStore,
                 prior_weight: float = _PRIOR_WEIGHT, min_specific: int = _MIN_SPECIFIC):
        self._base = base
        self._store = store
        self._k = prior_weight
        self._min_specific = min_specific

    def estimate(self, task: Task) -> Estimate:
        est = self._base.estimate(task)

        # prefer the specific recurring-item bucket; back off to category average
        n_s, _ms_a, ms_total = self._store.stats(signature(est.title, est.category))
        if n_s >= self._min_specific:
            n, mean_total, level = n_s, ms_total, "specific"
        else:
            n_g, _mg_a, mg_total = self._store.stats_category(est.category)
            if n_g > 0:
                n, mean_total, level = n_g, mg_total, "category"
            else:
                est.confidence = 0.0
                est.learn_level = ""
                return est

        w_obs = n / (n + self._k)
        w_prior = self._k / (n + self._k)

        # correct the total toward reality, scale components to preserve shape
        baseline_total = est.total
        if baseline_total > 0:
            corrected_total = est.total * w_prior + mean_total * w_obs
            s = corrected_total / baseline_total
            est.active = round(est.active * s)
            est.wait = round(est.wait * s)
            est.travel = round(est.travel * s)

        est.confidence = round(w_obs, 2)
        est.learn_level = level
        est.source = f"{est.source}+learned"
        return est
