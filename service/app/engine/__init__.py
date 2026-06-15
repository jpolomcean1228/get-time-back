"""Estimation engine.

Public estimators, all interchangeable behind the Estimator protocol:
    RulesEstimator   — deterministic baseline, no key required
    LLMEstimator     — Claude first-pass, falls back to rules
    LearnedEstimator — wraps either of the above, corrects toward actuals
"""
from .base import Estimate, Estimator, Task
from .rules import RulesEstimator
from .llm import LLMEstimator
from .learned import LearnedEstimator
from .levers import LEVERS, credit, kind
from .signature import signature

__all__ = [
    "Estimate", "Estimator", "Task",
    "RulesEstimator", "LLMEstimator", "LearnedEstimator",
    "LEVERS", "credit", "kind", "signature",
]
