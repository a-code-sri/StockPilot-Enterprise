"""
Single source of truth for permission names.

Convention: `<module>.read` grants read access to a module *and* its analytics;
`<module>.write` grants create/update/delete. Routers must only use names from
PERMISSIONS (enforced by tests/test_permissions.py).
"""

ADMIN_ROLE = "admin"

MODULES: dict[str, tuple[str, ...]] = {
    "inventory": ("read", "write"),
    "accounts": ("read", "write"),
    "delivery": ("read", "write"),
    "organization": ("read", "write"),
    "projects": ("read", "write"),
    "business": ("manage",),
    "ai": ("use",),
    "rbac": ("manage",),
}

PERMISSIONS: tuple[str, ...] = tuple(
    f"{module}.{action}" for module, actions in MODULES.items() for action in actions
)

# Permissions created by older versions. Seeding migrates roles off them and deletes them.
# Value = replacement permissions granted to roles that held the legacy one.
LEGACY_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "inventory.create": ("inventory.write",),
    "inventory.update": ("inventory.write",),
    "inventory.delete": ("inventory.write",),
    "organization": ("organization.read",),
    # Analytics are now gated by `<module>.read`; nothing to replace.
    "analytics.read": (),
}

# Which permission is needed to receive realtime events / analytics for a module.
MODULE_READ_PERMISSION = {
    "inventory": "inventory.read",
    "accounts": "accounts.read",
    "delivery": "delivery.read",
    "organization": "organization.read",
    "projects": "projects.read",
}
