"""The learned estimator — the heart of Phase 1.

It wraps any base estimator (rules or LLM) and corrects the first-pass numbers
toward what actually happened for similar tasks. The correction is a shrinkage
blend: trust the prior estimate when you have no history, trust observed reality
as samples accumulate.

    corrected = estimate * k/(k+n) + observed_mean * n/(k+n)

where n = number of recorded actuals for this category and k is a prior weight
(how many "phantom" estimate-observations to hold before reality dominates).
Confidence = n/(n+k), which is exactly the weight given to observed data — so
the number the UI shows as "confidence" is the same number doing the math.

This is deliberately the simplest honest version. Phase 2+ can swap the
signature from bare category to category+context and the mean to a recency-
weighted estimate without changing this interface.
"""
from __future__ import annotations

from .base import Estimate, Estimator, Task
from ..store.actuals import ActualsStore

_PRIOR_WEIGHT = 3.0  # k: samples needed before observed data is trusted ~50/50


class LearnedEstimator:
    def __init__(self, base: Estimator, store: ActualsStore, prior_weight: float = _PRIOR_WEIGHT):
        self._base = base
        self._store = store
        self._k = prior_weight

    def _signature(self, est: Estimate) -> str:
        # start simple: one bucket per category. Easy to enrich later.
        return est.category

    def estimate(self, task: Task) -> Estimate:
        est = self._base.estimate(task)
        n, _mean_active, mean_total = self._store.stats(self._signature(est))
        if n <= 0:
            est.confidence = 0.0
            return est

        w_obs = n / (n + self._k)          # weight on observed reality
        w_prior = self._k / (n + self._k)  # weight on the first-pass estimate

        # Correct the *total* toward what actually happened, then scale each
        # component by the same factor so the task's shape (active vs wait vs
        # travel) is preserved — only its magnitude moves toward reality.
        baseline_total = est.total
        if baseline_total > 0:
            corrected_total = est.total * w_prior + mean_total * w_obs
            s = corrected_total / baseline_total
            est.active = round(est.active * s)
            est.wait = round(est.wait * s)
            est.travel = round(est.travel * s)

        est.confidence = round(w_obs, 2)
        est.source = f"{est.source}+learned"
        return est
