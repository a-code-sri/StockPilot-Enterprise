from sqlalchemy.orm import declarative_base

# Shared declarative base. Model modules import this; this module must not import
# them back (that circular import used to be hidden by try/except). To register
# every table on Base.metadata, call backend.core.database.registry.import_all_models().
Base = declarative_base()
