"""Consent — the privacy gate on the household layer.

The moment the tool reads other people's availability and proposes they do
things, privacy stops being optional. Each member controls two switches:

  shares_availability — may the matcher see their free/busy at all?
  accepts_handoffs    — may the matcher propose tasks to them?

A member is only a candidate if BOTH are true. Default is closed: anyone not
explicitly opted in is invisible and un-proposable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemberConsent:
    shares_availability: bool = False
    accepts_handoffs: bool = False


class Consent:
    def __init__(self, by_member: dict[str, MemberConsent]):
        self._c = by_member

    def _get(self, member_id: str) -> MemberConsent:
        return self._c.get(member_id, MemberConsent())   # closed by default

    def shares(self, member_id: str) -> bool:
        return self._get(member_id).shares_availability

    def accepts(self, member_id: str) -> bool:
        return self._get(member_id).accepts_handoffs

    def is_candidate(self, member_id: str) -> bool:
        c = self._get(member_id)
        return c.shares_availability and c.accepts_handoffs
