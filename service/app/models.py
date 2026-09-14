"""API schemas."""
from __future__ import annotations

from typing import Optional

import re
from pydantic import BaseModel, Field, field_validator


class EnrichRequest(BaseModel):
    tasks: list[str] = Field(default_factory=list, max_length=200, description="One line per item, as written")
    include_calendar: bool = Field(default=False, description="Fold today's calendar events into the list")
    include_actions: bool = Field(default=False, description="Attach a proposed, reversible action to each item")
    now_min: Optional[int] = Field(default=None, ge=0, le=1439, description="Client-local minutes since midnight; server time if omitted")

    @field_validator("tasks")
    @classmethod
    def _cap_task_length(cls, v):
        if any(len(t) > 500 for t in v):
            raise ValueError("each task line must be 500 characters or fewer")
        return v


class ProposedAction(BaseModel):
    id: str
    type: str
    lever: str
    label: str              # the button verb
    detail: str             # human preview of what will happen
    body: str = ""          # optional draft text
    target: str = ""        # member id this is addressed to (Phase 4)
    reversible: bool = True
    status: str             # proposed | executed | undone
    result: str = ""        # executor's confirmation message


class CoordinationOut(BaseModel):
    helper: str             # member name
    window: str             # human time window
    reason: str             # why this person
    kind: str               # swap | handoff


class EnrichedTask(BaseModel):
    title: str
    when: str
    category: str
    active: int
    wait: int
    travel: int
    frag: int
    total: int
    lever: str
    lever_label: str
    why: str
    reclaim: int
    kind: str               # logistics | presence
    confidence: float       # 0..1, rises as the engine learns
    learn_level: str        # specific | category | "" — which bucket taught it
    source: str             # rules | llm | (+learned)
    action: Optional[ProposedAction] = None   # the move you can confirm (Phase 3)
    coordination: Optional[CoordinationOut] = None  # the matched helper (Phase 4)


class Totals(BaseModel):
    committed: int          # logistics minutes on the list
    reclaimable: int        # minutes the suggested moves return
    presence: int           # minutes flagged to defend


class EnrichResponse(BaseModel):
    tasks: list[EnrichedTask]
    totals: Totals
    engine: str             # which base estimator is active
    presence: Optional["PresencePlanOut"] = None   # the values loop (Phase 5)


class PresenceBlockOut(BaseModel):
    value: str              # what it's for
    minutes: int
    when: str               # human start time
    action: ProposedAction  # confirm to protect & defend it


class PresencePlanOut(BaseModel):
    reclaimable: int        # minutes the day's moves free up
    allocated: int          # minutes routed to protected presence
    banked: int             # freed minutes left unspent (not refilled)
    blocks: list[PresenceBlockOut]


class ValueIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    minutes: int = Field(ge=0, le=1440)
    when: str = Field(default="", description='24h "HH:MM", or empty')
    priority: int = Field(default=99, ge=0, le=9999)

    @field_validator("when")
    @classmethod
    def _valid_time(cls, v):
        if v and not re.fullmatch(r"[0-2]?\d:[0-5]\d", v):
            raise ValueError('when must be "HH:MM" or empty')
        return v


class ProfileIn(BaseModel):
    category: str
    active: int
    wait: int
    travel: int
    frag: int
    lever: str
    why: str = ""
    keywords: list[str] = Field(default_factory=list)
    default: bool = False


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    token: str
    name: str


class HouseholdCreateIn(BaseModel):
    name: str


class JoinIn(BaseModel):
    code: str


class MembershipIn(BaseModel):
    can_drive: bool = True
    shares_availability: bool = False
    accepts_handoffs: bool = False


class AvailabilityIn(BaseModel):
    busy: list[list[int]] = Field(default_factory=list, description="[[start_min, end_min], ...]")


class ActionRef(BaseModel):
    id: str


class ActualIn(BaseModel):
    title: str = Field(default="", description="The task as written — drives the specific bucket")
    category: str = Field(description="Task category — the fallback bucket")
    active_minutes: int
    total_minutes: int


class CalendarEvent(BaseModel):
    title: str
    start: str
    end: str
    minutes: int
    location: str = ""
    attendees: int = 1


# ---- Background agent (control-loop cycle output) ----

class ValueScoreOut(BaseModel):
    reclaimable: int
    presence_protected: int
    fragmentation: int
    banked: int
    score: float


class SuggestionOut(BaseModel):
    id: str
    kind: str               # protect | handoff | reclaim | warning
    title: str
    detail: str
    value_minutes: int
    urgency: str            # now | today | flexible
    interrupt: bool         # earns an interrupt vs. batched into the brief
    action_id: str = ""


class AgentBriefOut(BaseModel):
    headline: str
    score: ValueScoreOut
    suggestions: list[SuggestionOut]
    critique: list[str]
    interrupt_count: int
    brief_count: int


# ---- Feedback harness (the agent learns your restraint) ----

class FeedbackIn(BaseModel):
    suggestion_id: str = Field(min_length=1, max_length=128)
    kind: str = Field(min_length=1, max_length=32)
    value_minutes: int = Field(ge=0, le=100000)
    interrupt: bool         # was it surfaced as an interrupt?
    verdict: str            # accepted | rejected | edited | ignored
    edited_to: Optional[str] = Field(default=None, max_length=200)

    @field_validator("verdict")
    @classmethod
    def _known_verdict(cls, v):
        if v not in ("accepted", "rejected", "edited", "ignored"):
            raise ValueError("verdict must be accepted, rejected, edited, or ignored")
        return v


class FeedbackStatsOut(BaseModel):
    total: int
    by_kind: dict
    interrupt_min: int          # the learned interrupt threshold (default 45)
    suppressed_kinds: list[str]
    preferred_edits: dict       # signature -> what you keep changing it to
    learning_window_days: int   # only feedback newer than this shapes behavior


# ---- Inbox / commitment extraction (a real source) ----

class InboxIn(BaseModel):
    text: Optional[str] = Field(default=None, max_length=50000)   # paste a message/thread; omit to pull from the inbox


class CommitmentOut(BaseModel):
    task: str
    cue: str                     # request | reminder | deadline | task | llm
    confidence: float
    source: str = ""


class InboxOut(BaseModel):
    commitments: list[CommitmentOut]
    source: str                  # pasted text | mock inbox | gmail


# ---- Weekly time-back ledger ----

class WeekPointOut(BaseModel):
    week_start: str
    label: str
    reclaimed: int
    protected: int
    total: int
    count: int


class TimeBackReportOut(BaseModel):
    weeks: list[WeekPointOut]
    this_week: WeekPointOut
    delta_total: int
    lifetime: dict
    insight: str
