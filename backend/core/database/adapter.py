from backend.core.database.session import SessionLocal

class DatabaseAdapter:

    @staticmethod
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()