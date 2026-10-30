import importlib
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.core.auth.jwt_handler import create_access_token, decode_access_token
from backend.core.auth.security import hash_password, verify_password
from backend.core.rbac.permissions import LEGACY_PERMISSIONS, PERMISSIONS
from backend.core.rbac.service import RBACService
from backend.outbox import repository as outbox

ROOT = Path(__file__).resolve().parents[2]


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery")
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x", "not-a-hash")


def test_long_passwords_do_not_crash():
    # bcrypt>=5 raises on >72 bytes; we truncate consistently instead.
    h = hash_password("é" * 60)
    assert verify_password("é" * 60, h)


def test_jwt_roundtrip_and_tamper():
    token = create_access_token({"sub": "alice"})
    assert decode_access_token(token)["sub"] == "alice"
    assert decode_access_token(token[:-2] + "xx") is None


def test_every_permission_used_in_code_exists():
    used = set()
    for path in (ROOT / "backend").rglob("*.py"):
        used |= set(re.findall(r'require_permission\("([^"]+)"\)', path.read_text(encoding="utf-8")))
    assert used, "expected to find require_permission calls"
    assert used <= set(PERMISSIONS), used - set(PERMISSIONS)


def test_legacy_replacements_exist():
    for repls in LEGACY_PERMISSIONS.values():
        assert set(repls) <= set(PERMISSIONS)


def _user(*roles):
    return SimpleNamespace(
        roles=[SimpleNamespace(name=n, permissions=[SimpleNamespace(name=p) for p in perms]) for n, perms in roles]
    )


def test_admin_gets_everything_and_others_get_their_roles():
    assert RBACService.get_user_permissions(_user(("admin", []))) == set(PERMISSIONS)
    clerk = _user(("clerk", ["inventory.read"]), ("viewer", ["accounts.read"]))
    assert RBACService.get_user_permissions(clerk) == {"inventory.read", "accounts.read"}
    assert not RBACService.has_permission(clerk, "inventory.write")


def test_unknown_permission_fails_fast():
    from backend.core.rbac.dependencies import require_permission

    with pytest.raises(ValueError):
        require_permission("inventory.delete")


class _FakeDB:
    def flush(self):
        pass


def test_outbox_backoff_and_dead_letter():
    assert [outbox.backoff_seconds(a) for a in range(4)] == [10, 20, 40, 80]
    assert outbox.backoff_seconds(20, cap=300) == 300

    row = SimpleNamespace(attempts=0, status="processing", last_error=None, available_at=None, updated_at=None,
                          locked_at=None)
    for _ in range(2):
        assert outbox.mark_failed(_FakeDB(), row, error_message="boom", max_attempts=3) == outbox.FAILED
    assert outbox.mark_failed(_FakeDB(), row, error_message="boom", max_attempts=3) == outbox.DEAD
    assert row.attempts == 3

    row2 = SimpleNamespace(attempts=0, status="processing", last_error=None, available_at=None, updated_at=None,
                           locked_at=None)
    assert outbox.mark_failed(_FakeDB(), row2, error_message="x", max_attempts=8, permanent=True) == outbox.DEAD


def test_dispatcher_rejects_unknown_modules():
    from backend.workers.dispatcher import HandlerNotFound, resolve_handler

    with pytest.raises(HandlerNotFound):
        resolve_handler("os", "system")
    handler, fallback = resolve_handler("accounts", "transaction_created")
    assert handler.__name__ == "handle_transaction_created" and not fallback
    _, fallback = resolve_handler("accounts", "something_new")
    assert fallback


def test_app_imports_and_routes_registered():
    main = importlib.import_module("backend.main")
    paths = main.app.openapi()["paths"]
    for p in ["/auth/login", "/rbac/users/{user_id}/roles", "/business/profile", "/ai/chat",
              "/inventory/{item_id}", "/analytics/projects/overview", "/health"]:
        assert p in paths
