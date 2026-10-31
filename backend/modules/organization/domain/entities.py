from typing import Callable, Optional


class OrganizationError(ValueError):
    pass


def would_create_cycle(employee_db_id: int, new_manager_db_id: Optional[int], manager_of: Callable[[int], Optional[int]]) -> bool:
    """
    True if making `new_manager_db_id` the manager of `employee_db_id` creates a
    reporting loop (e.g. A -> B -> A). `manager_of(x)` returns x's current manager id.
    """
    seen = set()
    current = new_manager_db_id
    while current is not None:
        if current == employee_db_id:
            return True
        if current in seen:  # pre-existing loop elsewhere; stop walking
            return False
        seen.add(current)
        current = manager_of(current)
    return False
