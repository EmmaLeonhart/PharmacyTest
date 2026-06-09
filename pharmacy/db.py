"""Engine and session helpers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pharmacy.models import Base


def init_db(url="sqlite:///pharmacy.db"):
    """Create the engine and all tables; return the engine."""
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine


def make_session(engine):
    """Return a new Session bound to the engine."""
    Session = sessionmaker(bind=engine, future=True)
    return Session()
