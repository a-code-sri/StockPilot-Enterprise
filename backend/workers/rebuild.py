"""
Rebuild utilities (skeleton).

Later, you'll add functions like:
- rebuild_accounts_projections(db, from_date=None, to_date=None)
- rebuild_inventory_projections(...)
"""

from backend.core.database.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        # TODO: call rebuild functions once projection tables exist
        print("Rebuild not implemented yet. Add rebuild_* functions when projections exist.")
    finally:
        db.close()


if __name__ == "__main__":
    main()