"""Mock values loader — seeds the stated-values store from a fixture."""
from __future__ import annotations

import json
from pathlib import Path

from .values import Value, ValuesStore

_FX = Path(__file__).resolve().parents[1] / "fixtures" / "values.json"


def load_mock_values() -> ValuesStore:
    raw = json.loads(_FX.read_text())
    return ValuesStore([Value(**v) for v in raw])
