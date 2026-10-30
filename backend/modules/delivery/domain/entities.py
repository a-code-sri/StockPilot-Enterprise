from enum import Enum


class DeliveryStatus(str, Enum):
    pending = "pending"
    packed = "packed"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    cancelled = "cancelled"


ACTIVE_STATUSES = {DeliveryStatus.pending, DeliveryStatus.packed, DeliveryStatus.out_for_delivery}
FINISHED_STATUSES = {DeliveryStatus.delivered, DeliveryStatus.failed, DeliveryStatus.cancelled}

# Allowed status changes. delivered/cancelled are terminal; a failed delivery can
# be re-opened (back to pending) for another attempt, or cancelled.
TRANSITIONS: dict[DeliveryStatus, frozenset[DeliveryStatus]] = {
    DeliveryStatus.pending: frozenset({DeliveryStatus.packed, DeliveryStatus.cancelled}),
    DeliveryStatus.packed: frozenset({DeliveryStatus.pending, DeliveryStatus.out_for_delivery, DeliveryStatus.cancelled}),
    DeliveryStatus.out_for_delivery: frozenset({DeliveryStatus.delivered, DeliveryStatus.failed}),
    DeliveryStatus.failed: frozenset({DeliveryStatus.pending, DeliveryStatus.cancelled}),
    DeliveryStatus.delivered: frozenset(),
    DeliveryStatus.cancelled: frozenset(),
}

# Stock leaves the warehouse when the order is dispatched...
DEDUCT_STOCK_ON = DeliveryStatus.out_for_delivery
# ...and comes back if the delivery does not complete.
RETURN_STOCK_ON = frozenset({DeliveryStatus.failed, DeliveryStatus.cancelled})


class InvalidTransition(ValueError):
    pass


def check_transition(current: str, new: str) -> None:
    cur, nxt = DeliveryStatus(current), DeliveryStatus(new)
    if nxt not in TRANSITIONS[cur]:
        allowed = ", ".join(sorted(s.value for s in TRANSITIONS[cur])) or "none (final status)"
        raise InvalidTransition(f"Cannot change status from '{cur.value}' to '{nxt.value}'. Allowed: {allowed}")


def allowed_next(current: str) -> list[str]:
    return sorted(s.value for s in TRANSITIONS[DeliveryStatus(current)])
