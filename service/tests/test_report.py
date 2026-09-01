"""Weekly time-back ledger: totals, deltas, and what counts as realized."""
from datetime import datetime, timedelta

from app.agent.report import build_report

NOW = datetime(2026, 8, 26, 12, 0)   # a Wednesday — its week starts Mon Aug 24


def _row(days_ago, kind, mins, verdict="accepted"):
    d = (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
    return {"created_at": d, "kind": kind, "value_minutes": mins,
            "verdict": verdict, "interrupt": 1}


def test_realized_totals_this_week():
    rows = [_row(0, "handoff", 65), _row(1, "reclaim", 30), _row(2, "protect", 45)]
    r = build_report(rows, weeks=4, now=NOW)
    assert r["this_week"]["reclaimed"] == 95      # handoff + reclaim
    assert r["this_week"]["protected"] == 45
    assert r["this_week"]["total"] == 140
    assert r["lifetime"]["total"] == 140


def test_rejected_and_ignored_do_not_count():
    rows = [_row(0, "reclaim", 100, "rejected"), _row(0, "handoff", 50, "ignored")]
    r = build_report(rows, now=NOW)
    assert r["lifetime"]["total"] == 0


def test_edited_counts_as_realized():
    r = build_report([_row(0, "handoff", 40, "edited")], now=NOW)
    assert r["this_week"]["reclaimed"] == 40


def test_delta_vs_last_week():
    rows = [_row(1, "reclaim", 60), _row(8, "reclaim", 20)]   # 60 this wk, 20 last wk
    r = build_report(rows, weeks=4, now=NOW)
    assert r["delta_total"] == 40


def test_weeks_are_continuous_and_ordered():
    r = build_report([], weeks=6, now=NOW)
    assert len(r["weeks"]) == 6
    starts = [w["week_start"] for w in r["weeks"]]
    assert starts == sorted(starts)               # oldest -> newest
    assert r["weeks"][-1]["week_start"] == "2026-08-24"   # current week last


def test_empty_gives_guidance():
    assert "accept a suggestion" in build_report([], now=NOW)["insight"]
