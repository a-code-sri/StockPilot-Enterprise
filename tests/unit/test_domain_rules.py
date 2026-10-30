import pytest

from backend.modules.delivery.domain.entities import InvalidTransition, allowed_next, check_transition
from backend.modules.inventory.domain.entities import InventoryError, apply_movement
from backend.modules.organization.domain.entities import would_create_cycle


# ---------------- inventory ----------------

def test_add_fulfils_on_order_first():
    s = apply_movement(10, 5, "add", 8)
    assert (s.quantity, s.on_order_quantity) == (18, 0)


def test_consume_and_deliver_reduce_stock():
    assert apply_movement(10, 0, "consume", 4).quantity == 6
    s = apply_movement(4, 0, "deliver", 4)
    assert s.quantity == 0 and s.becomes_consumed


def test_cannot_go_negative():
    with pytest.raises(InventoryError, match="Insufficient"):
        apply_movement(3, 0, "consume", 4)


def test_order_and_return():
    assert apply_movement(1, 2, "order", 5).on_order_quantity == 7
    s = apply_movement(1, 2, "return", 5)
    assert (s.quantity, s.on_order_quantity) == (6, 2)


@pytest.mark.parametrize("action,amount", [("consume", 0), ("teleport", 1)])
def test_invalid_movements(action, amount):
    with pytest.raises(InventoryError):
        apply_movement(5, 0, action, amount)


# ---------------- delivery ----------------

def test_happy_path_transitions():
    for a, b in [("pending", "packed"), ("packed", "out_for_delivery"), ("out_for_delivery", "delivered")]:
        check_transition(a, b)


@pytest.mark.parametrize("a,b", [("delivered", "pending"), ("cancelled", "packed"), ("pending", "delivered")])
def test_illegal_transitions(a, b):
    with pytest.raises(InvalidTransition):
        check_transition(a, b)


def test_failed_can_be_retried():
    assert allowed_next("failed") == ["cancelled", "pending"]
    assert allowed_next("delivered") == []


# ---------------- organization ----------------

def test_manager_cycle_detection():
    managers = {2: 1, 3: 2, 1: None}  # 3 -> 2 -> 1
    get = managers.get
    assert would_create_cycle(1, 3, get)       # 1 reporting to 3 closes the loop
    assert not would_create_cycle(3, 1, get)   # 3 reporting to 1 is fine
    assert not would_create_cycle(1, None, get)
