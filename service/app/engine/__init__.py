"""Estimation engine.

Public estimators, all interchangeable behind the Estimator protocol:
    RulesEstimator   — deterministic baseline, no key required
    LLMEstimator     — Claude first-pass, falls back to rules
    LearnedEstimator — wraps either of the above, corrects toward actuals

Two pieces of domain knowledge are now data, not code:
    profiles  — the category/cost table (fixtures/profiles.json)
    levers    — the move + credit registry
"""
from .base import Estimate, Estimator, Task
from .rules import RulesEstimator
from .llm import LLMEstimator
from .learned import LearnedEstimator
from .levers import LEVERS, Lever, credit, kind, lever_label, register_lever
from .profiles import Profile, ProfileStore, default_profiles, load_profiles
from .signature import signature

__all__ = [
    "Estimate", "Estimator", "Task",
    "RulesEstimator", "LLMEstimator", "LearnedEstimator",
    "LEVERS", "Lever", "credit", "kind", "lever_label", "register_lever",
    "Profile", "ProfileStore", "default_profiles", "load_profiles",
    "signature",
]
