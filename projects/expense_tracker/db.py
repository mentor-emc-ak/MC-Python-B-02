import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_DB_PATH = "expense_tracker.db"


def get_engine(db_path=None):
    path = db_path or os.environ.get("EXPENSE_TRACKER_DB", DEFAULT_DB_PATH)
    return create_engine(f"sqlite:///{path}", echo=False)


def make_session_factory(db_path=None) -> sessionmaker:
    engine = get_engine(db_path)
    from .models import Base

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
