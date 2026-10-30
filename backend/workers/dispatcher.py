from __future__ import annotations

import importlib
from typing import Any, Callable

from sqlalchemy.orm import Session

# Only these modules may be resolved from outbox rows (the module name is data).
KNOWN_MODULES = frozenset({"accounts", "inventory", "delivery", "organization", "projects"})


class HandlerNotFound(Exception):
    """Permanent failure: no handler exists, retrying will not help."""


def _sanitize_event_type(event_type: str) -> str:
    return event_type.strip().lower().replace(".", "_").replace("-", "_").replace(" ", "_")


def resolve_handler(module: str, event_type: str) -> tuple[Callable[..., Any], bool]:
    """Returns (handler, is_fallback)."""
    if module not in KNOWN_MODULES:
        raise HandlerNotFound(f"Unknown analytics module '{module}'")

    module_path = f"backend.modules.{module}.analytics"
    mod = importlib.import_module(module_path)

    handler = getattr(mod, f"handle_{_sanitize_event_type(event_type)}", None)
    if callable(handler):
        return handler, False

    fallback = getattr(mod, "handle_event", None)
    if callable(fallback):
        return fallback, True

    raise HandlerNotFound(f"No handler for {module}.{event_type} in {module_path}")


def dispatch(*, db: Session, module: str, event_type: str, payload: dict[str, Any], outbox_id: int) -> None:
    handler, is_fallback = resolve_handler(module, event_type)
    if is_fallback:
        handler(db=db, event_type=event_type, payload=payload, outbox_id=outbox_id)
    else:
        handler(db=db, payload=payload, outbox_id=outbox_id)
