from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session


class HandlerNotFound(Exception):
    pass


def _sanitize_event_type(event_type: str) -> str:
    return (
        event_type.strip()
        .lower()
        .replace(".", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


@dataclass(frozen=True)
class DispatchTarget:
    module: str
    event_type: str

    @property
    def analytics_module_path(self) -> str:
        # FIX: your modules are under backend.modules.<module>
        return f"backend.modules.{self.module}.analytics"

    @property
    def handler_name(self) -> str:
        return f"handle_{_sanitize_event_type(self.event_type)}"


def resolve_handler(module: str, event_type: str) -> Callable[..., Any]:
    target = DispatchTarget(module=module, event_type=event_type)

    try:
        mod = importlib.import_module(target.analytics_module_path)
    except Exception as e:
        raise HandlerNotFound(
            f"Cannot import analytics module '{target.analytics_module_path}': {e}"
        ) from e

    handler = getattr(mod, target.handler_name, None)
    if callable(handler):
        return handler

    fallback = getattr(mod, "handle_event", None)
    if callable(fallback):
        return fallback

    raise HandlerNotFound(
        f"No handler found: {target.analytics_module_path}.{target.handler_name} "
        f"(and no handle_event fallback)"
    )


def dispatch(
    *,
    db: Session,
    module: str,
    event_type: str,
    payload: dict[str, Any],
    outbox_id: int,
) -> None:
    handler = resolve_handler(module, event_type)

    if getattr(handler, "__name__", "") == "handle_event":
        handler(db=db, event_type=event_type, payload=payload, outbox_id=outbox_id)
        return

    handler(db=db, payload=payload, outbox_id=outbox_id)