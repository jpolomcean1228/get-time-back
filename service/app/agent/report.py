"""The weekly time-back ledger — the payoff the whole system builds toward.

"You saved 90 minutes" is just a number work quietly reabsorbs. A ledger that
totals it week over week makes the invisible visible. This counts what you
*acted on* — accepted or edited suggestions — because that's time actually
reclaimed or presence actually defended, not merely proposed. Reclaim + handoff
minutes are time freed; protect minutes are presence kept. Both are the asset.
"""
from __future__ import annotations

from datetime import datetime, timedelta

_REALIZED = ("accepted", "edited")     # a rejected/ignored suggestion returned nothing


def _week_start(d):
    return d - timedelta(days=d.weekday())      # Monday of that week


def _insight(this_week, lifetime):
    if this_week["total"] == 0:
        return ("No time reclaimed yet this week — accept a suggestion in the brief "
                "and it lands here.")
    parts = []
    if this_week["reclaimed"] >= this_week["protected"]:
        parts.append(f"Most of your week back came from freeing time "
                     f"({this_week['reclaimed']} min).")
    else:
        parts.append(f"You defended more presence than you freed "
                     f"({this_week['protected']} min protected).")
    if this_week["reclaimed"] > 0 and this_week["protected"] == 0:
        parts.append("You reclaimed time but protected none — point some of it at "
                     "a #protect block you'll actually keep.")
    elif this_week["protected"] > 0:
        parts.append(f"You protected {this_week['protected']} min of presence — "
                     "that's the win to defend next week.")
    return " ".join(parts)


def build_report(rows, weeks=8, now=None):
    now = now or datetime.now()
    cur_start = _week_start(now.date())
    starts = [cur_start - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    buckets = {s: {"reclaimed": 0, "protected": 0, "count": 0} for s in starts}
    life = {"reclaimed": 0, "protected": 0}

    for r in rows:
        if r["verdict"] not in _REALIZED:
            continue
        try:
            d = datetime.strptime(str(r["created_at"])[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        mins = int(r["value_minutes"])
        freed = r["kind"] in ("reclaim", "handoff")
        if freed:
            life["reclaimed"] += mins
        elif r["kind"] == "protect":
            life["protected"] += mins
        ws = _week_start(d)
        if ws in buckets:
            b = buckets[ws]
            if freed:
                b["reclaimed"] += mins
            elif r["kind"] == "protect":
                b["protected"] += mins
            b["count"] += 1

    weeks_out = []
    for s in starts:
        b = buckets[s]
        weeks_out.append({
            "week_start": s.isoformat(),
            "label": s.strftime("%b %d").replace(" 0", " "),
            "reclaimed": b["reclaimed"], "protected": b["protected"],
            "total": b["reclaimed"] + b["protected"], "count": b["count"]})

    this_week = weeks_out[-1]
    last_week = weeks_out[-2] if len(weeks_out) >= 2 else {"total": 0}
    return {
        "weeks": weeks_out,
        "this_week": this_week,
        "delta_total": this_week["total"] - last_week["total"],
        "lifetime": {"reclaimed": life["reclaimed"], "protected": life["protected"],
                     "total": life["reclaimed"] + life["protected"]},
        "insight": _insight(this_week, life)}
