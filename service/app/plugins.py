"""A tiny plugin registry for the service's swappable components.

Phase 1-5 wired every swappable seam — the base estimator, the calendar
provider, the calendar writer, the message writer — by hand in `main.py`:
nested constructors plus `if env/credentials` branches choosing mock vs real.
Adding or swapping an implementation meant editing that assembly.

Here each seam is a *kind*, and an implementation registers itself under a
name with a factory:

    register("calendar", "mock",  lambda cfg: MockCalendarProvider())
    register("calendar", "google", lambda cfg: GoogleCalendarProvider(cfg["credentials"]))

`main.py` then builds a component by name (`create("calendar", name, cfg)`)
instead of constructing it directly. A new adapter — including a third-party
one shipped in its own package — becomes available simply by registering it;
the assembly never changes. External plugin modules listed in `GTB_PLUGINS`
(comma-separated) are imported at startup so their `register(...)` calls run.

The factory takes one argument, a `config` dict, so an implementation that
needs credentials or paths reads them from there rather than from globals.
"""
from __future__ import annotations

import importlib
import os
from typing import Any, Callable

# factory: config dict -> a built component instance
Factory = Callable[[dict], Any]

# kind -> { name -> factory }
_REGISTRY: dict[str, dict[str, Factory]] = {}


def register(kind: str, name: str, factory: Factory) -> None:
    """Register (or replace) an implementation of `kind` under `name`."""
    _REGISTRY.setdefault(kind, {})[name] = factory


def names(kind: str) -> list[str]:
    """The registered implementation names for a kind, sorted."""
    return sorted(_REGISTRY.get(kind, {}))


def has(kind: str, name: str) -> bool:
    return name in _REGISTRY.get(kind, {})


def create(kind: str, name: str, config: dict | None = None) -> Any:
    """Build the named implementation of `kind`. Raises LookupError if unknown."""
    try:
        factory = _REGISTRY[kind][name]
    except KeyError:
        raise LookupError(
            f"No {kind!r} plugin named {name!r}. Registered: {names(kind)}"
        )
    return factory(config or {})


def summary() -> dict[str, list[str]]:
    """Every kind and the names registered under it — what the API exposes."""
    return {kind: names(kind) for kind in sorted(_REGISTRY)}


def load_external(spec: str | None = None) -> list[str]:
    """Import the comma-separated plugin modules so they self-register.

    Defaults to the `GTB_PLUGINS` env var. Each module is imported for its
    side effect (its top-level `register(...)` calls). Returns the modules
    actually imported.
    """
    spec = os.environ.get("GTB_PLUGINS", "") if spec is None else spec
    loaded: list[str] = []
    for mod in (m.strip() for m in spec.split(",")):
        if mod:
            importlib.import_module(mod)
            loaded.append(mod)
    return loaded


def register_builtins() -> None:
    """Register the implementations that ship with the service.

    Imports are local so this module stays dependency-light and import-cycle
    free; it is called once at startup. Re-registering is harmless (idempotent).
    """
    from .engine import LLMEstimator, RulesEstimator
    register("estimator", "rules", lambda c: RulesEstimator())
    register("estimator", "llm", lambda c: LLMEstimator())

    from .calendar import (GoogleCalendarProvider, GoogleCalendarWriter,
                           MockCalendarProvider, MockCalendarWriter)
    register("calendar", "mock", lambda c: MockCalendarProvider())
    register("calendar", "google",
             lambda c: GoogleCalendarProvider(c["credentials"], c.get("token", "token.json")))
    register("calendar_writer", "mock", lambda c: MockCalendarWriter())
    register("calendar_writer", "google",
             lambda c: GoogleCalendarWriter(c["credentials"], c.get("token", "token_write.json")))

    from .messaging import GmailMessageWriter, MockMessageWriter
    register("message_writer", "mock", lambda c: MockMessageWriter())
    register("message_writer", "gmail",
             lambda c: GmailMessageWriter(c["credentials"], c.get("token", "token_gmail.json")))
