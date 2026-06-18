"""A stand-in third-party plugin, used by test_plugins to prove that a module
named in GTB_PLUGINS self-registers on import without touching the service."""
from app.plugins import register

register("estimator", "sample", lambda cfg: f"sample:{cfg.get('tag', 'none')}")
