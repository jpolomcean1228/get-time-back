"""Commitment extraction — the hidden to-dos buried in messages.

The tasks that eat your time are rarely on a list: they're a line in an email
("can you send the form by Friday"), a text ("don't forget the dentist"), a
note. This pulls those out as candidate task lines the agent can cost and route
like anything else.

Deterministic by default so it runs locally with nothing leaving the machine —
which matters when the source is your inbox. An LLM pass (Claude) is opt-in
behind GTB_AGENT_LLM=1 and only improves recall; it falls back to the rules on
any failure. Extraction is read-only and never sends anything.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

_VERBS = (r"(send|book|schedule|sign|submit|reply|rsvp|respond|call|email|pick up|"
          r"drop off|pay|order|bring|return|renew|confirm|register|fill out|fill in|"
          r"complete|review|forward|upload|print|buy|cancel|reschedule|approve|share|"
          r"update|finish|mail|text|ping|follow up|drop off|drop|grab|get)")

_REQUEST = re.compile(r"\b(can|could|would|will)\s+you\b|\bplease\b|\b(need|want)\s+you\s+to\b"
                      r"|\bcan\s+we\b|\bwhen\s+you\s+get\s+a\s+chance\b|\bmind\s+\w+ing\b", re.I)
_REMIND = re.compile(r"\bdon'?t\s+forget(\s+to)?\b|\bremember\s+to\b|\bmake\s+sure(\s+to)?\b"
                     r"|\bbe\s+sure\s+to\b|\bheads?\s*up\b", re.I)
_IMPERATIVE = re.compile(r"^\s*(?:also\s+|and\s+|pls\s+|plz\s+|then\s+)?" + _VERBS + r"\b", re.I)
_VERB_ANY = re.compile(r"\b" + _VERBS + r"\b", re.I)
_DEADLINE = re.compile(
    r"\b(by|before|due|this|next|on|until)\s+"
    r"(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|tomorrow|today|tonight|eod|noon|end\s+of\s+(the\s+)?(day|week|month)|\d{1,2}(:\d{2})?\s*(am|pm)?)\b"
    r"|\bdue\b|\basap\b|\bthis\s+(week|weekend|month)\b", re.I)

_STRIP_LEAD = re.compile(
    r"^(?:.*?\b(?:can|could|would|will)\s+you\s+|.*?\bplease\s+"
    r"|.*?\b(?:don'?t\s+forget\s+to|remember\s+to|make\s+sure\s+to|be\s+sure\s+to"
    r"|need\s+you\s+to|want\s+you\s+to)\s+)", re.I)


@dataclass
class Commitment:
    task: str
    cue: str            # request | reminder | deadline | task
    confidence: float
    source: str = ""


def _clauses(text):
    parts = re.split(r"[\n\r]+|(?<=[.!?;])\s+", text)
    return [p.strip(" \t-\u2013\u2014\u2022*>|") for p in parts if p.strip()]


def _to_task(clause, has_deadline_m):
    c = _STRIP_LEAD.sub("", clause, count=1)
    c = re.sub(r"\s+", " ", c).strip(" ?.!,;")
    if not c:
        return ""
    c = c[0].upper() + c[1:]
    if has_deadline_m:
        dl = has_deadline_m.group(0)
        if dl.lower() not in c.lower():
            c = f"{c} ({dl})"
    return c[:90]


def _rule_extract(text):
    out = []
    for clause in _clauses(text):
        req, rem = _REQUEST.search(clause), _REMIND.search(clause)
        imp, verb = _IMPERATIVE.search(clause), _VERB_ANY.search(clause)
        dl = _DEADLINE.search(clause)
        actiony = bool(imp or verb or dl)
        if (req or rem) and actiony:
            cue, conf = ("request" if req else "reminder"), 0.8
        elif imp:
            cue, conf = "task", 0.65
        elif dl and verb:
            cue, conf = "deadline", 0.6
        else:
            continue
        if dl:
            conf = min(conf + 0.1, 0.95)
        task = _to_task(clause, dl)
        if task:
            out.append(Commitment(task=task, cue=cue, confidence=round(conf, 2)))
    return out


def _llm_on():
    return (os.environ.get("GTB_AGENT_LLM", "").lower() in ("1", "true", "yes")
            and bool(os.environ.get("ANTHROPIC_API_KEY")))


def _llm_extract(text):
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=os.environ.get("GTB_MODEL", "claude-sonnet-4-6"), max_tokens=400,
            system=("Extract concrete commitments or to-dos a person owes from the text. "
                    "Return ONLY a JSON array of short imperative task strings (e.g. "
                    "[\"Send the Q3 numbers by Tuesday\"]). No prose, no code fences. "
                    "Empty array if none."),
            messages=[{"role": "user", "content": text[:4000]}])
        raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        raw = re.sub(r"^```(json)?|```$", "", raw).strip()
        tasks = json.loads(raw)
        return [Commitment(task=str(t)[:90], cue="llm", confidence=0.9)
                for t in tasks if str(t).strip()]
    except Exception:
        return None


def extract(text, source=""):
    if not text or not text.strip():
        return []
    items = (_llm_extract(text) if _llm_on() else None) or _rule_extract(text)
    seen, deduped = set(), []
    for c in items:
        key = c.task.lower()
        if key in seen:
            continue
        seen.add(key)
        c.source = source or c.source
        deduped.append(c)
    return deduped
