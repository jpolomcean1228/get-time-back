"""Household coordination layer (Phase 4)."""
from .roster import Household, Member
from .timemap import TimeMap, task_minutes, parse_clock, fmt
from .consent import Consent, MemberConsent
from .matcher import Matcher, Coordination
from .mock import load_mock_household

__all__ = [
    "Household", "Member", "TimeMap", "task_minutes", "parse_clock", "fmt",
    "Consent", "MemberConsent", "Matcher", "Coordination", "load_mock_household",
]
