"""Critic — the agent interrogates its own plan before you see it.

Deterministic self-checks that catch a weak plan internally rather than
spending your trust on it. An LLM strategic critique slots in behind
_llm_note() (off by default; enable with GTB_AGENT_LLM=1) — same mock-first
pattern as the estimator.
"""
from __future__ import annotations

import os


def critique(tasks, presence, suggestions) -> list[str]:
    notes: list[str] = []
    reclaimable = presence.reclaimable if presence else 0
    allocated = presence.allocated if presence else 0

    if reclaimable >= 60 and allocated == 0:
        notes.append("You'd reclaim time but protect none of it \u2014 add something that "
                     "matters so it doesn't just refill.")
    handoffs = [s for s in suggestions if s.kind == "handoff"]
    if len(handoffs) >= 3:
        notes.append("You're handing a lot off today \u2014 check it's genuinely a swap, "
                     "not just moving load onto someone else.")
    interrupts = [s for s in suggestions if s.interrupt]
    if len(interrupts) > 3:
        notes.append(f"{len(interrupts)} moves want a decision now; only the top few should "
                     "interrupt \u2014 the rest belong in the brief.")
    if allocated > 0:
        notes.append(f"Protecting {allocated} min of presence today \u2014 that's the win to defend.")

    extra = _llm_note(tasks, presence, suggestions)
    if extra:
        notes.append(extra)
    return notes


def _llm_note(tasks, presence, suggestions) -> str:
    """Optional strategic critique from Claude. Off unless GTB_AGENT_LLM=1."""
    if os.environ.get("GTB_AGENT_LLM", "").lower() not in ("1", "true", "yes"):
        return ""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic()
        summary = "; ".join(f"{s.kind}:{s.value_minutes}m" for s in suggestions[:8])
        msg = client.messages.create(
            model=os.environ.get("GTB_MODEL", "claude-sonnet-4-6"), max_tokens=120,
            system=("You review a day-plan for a tool whose goal is protecting presence, "
                    "not doing more. Reply with ONE short sentence of strategic critique, "
                    "or an empty string if the plan looks sound."),
            messages=[{"role": "user", "content": f"Moves: {summary}. "
                       f"Reclaimable {getattr(presence,'reclaimable',0)}m, "
                       f"protected {getattr(presence,'allocated',0)}m."}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception:
        return ""
