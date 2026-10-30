from backend.core.database.session import SessionLocal


def get_db():
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseAdapter:
    # Kept so existing `Depends(DatabaseAdapter.get_db)` call sites keep working.
    get_db = staticmethod(get_db)
