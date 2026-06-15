"""API schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EnrichRequest(BaseModel):
    tasks: list[str] = Field(default_factory=list, description="One line per item, as written")
    include_calendar: bool = Field(default=False, description="Fold today's calendar events into the list")
    include_actions: bool = Field(default=False, description="Attach a proposed, reversible action to each item")


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
    id: str
    label: str
    minutes: int
    when: str               # 24h "HH:MM"
    priority: int = 99


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
