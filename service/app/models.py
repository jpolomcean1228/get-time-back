"""API schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EnrichRequest(BaseModel):
    tasks: list[str] = Field(default_factory=list, description="One line per item, as written")
    include_calendar: bool = Field(default=False, description="Fold today's calendar events into the list")


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
    source: str             # rules | llm | (+learned)


class Totals(BaseModel):
    committed: int          # logistics minutes on the list
    reclaimable: int        # minutes the suggested moves return
    presence: int           # minutes flagged to defend


class EnrichResponse(BaseModel):
    tasks: list[EnrichedTask]
    totals: Totals
    engine: str             # which base estimator is active


class ActualIn(BaseModel):
    category: str = Field(description="Signature to learn against (e.g. the task category)")
    active_minutes: int
    total_minutes: int


class CalendarEvent(BaseModel):
    title: str
    start: str
    end: str
    minutes: int
    location: str = ""
    attendees: int = 1
