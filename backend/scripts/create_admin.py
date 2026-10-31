"""
Create (or promote) an admin user interactively.

    python -m backend.scripts.create_admin
    python -m backend.scripts.create_admin --username alice --email alice@example.com
"""

import argparse
import getpass
import sys

from backend.core.auth.models import User
from backend.core.auth.security import hash_password
from backend.core.database.registry import import_all_models
from backend.core.database.session import SessionLocal
from backend.core.rbac.models import Role
from backend.core.rbac.permissions import ADMIN_ROLE
from backend.core.rbac.seed import seed_rbac


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username")
    parser.add_argument("--email")
    args = parser.parse_args()

    import_all_models()

    username = args.username or input("Username: ").strip()
    db = SessionLocal()
    try:
        seed_rbac(db)
        admin_role = db.query(Role).filter_by(name=ADMIN_ROLE).one()
        user = db.query(User).filter(User.username == username).first()

        if user is None:
            email = args.email or input("Email: ").strip()
            password = getpass.getpass("Password (min 8 chars): ")
            if len(password) < 8 or len(password.encode()) > 72:
                print("Password must be 8-72 bytes.", file=sys.stderr)
                return 1
            user = User(username=username, email=email.lower(), hashed_password=hash_password(password), is_active=True)
            db.add(user)

        if admin_role not in user.roles:
            user.roles.append(admin_role)
        user.is_active = True
        db.commit()
        print(f"'{username}' is now an active admin.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
