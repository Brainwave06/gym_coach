"""
SQL Server connection manager with connection caching, timeouts,
and availability checks for Gym AI.
"""

import logging
import time
from contextlib import contextmanager
from typing import Generator, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from gym_ai.config import (
    DB_CONNECT_TIMEOUT,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
)

logger = logging.getLogger("gym_ai.database")

host_str = f"{DB_HOST}:{DB_PORT}" if DB_PORT else DB_HOST

if DB_USER and DB_PASSWORD:
    DATABASE_URL = (
        f"mssql+pyodbc://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{host_str}/{DB_NAME}"
        f"?driver=ODBC+Driver+18+for+SQL+Server"
        f"&TrustServerCertificate=yes"
        f"&timeout={DB_CONNECT_TIMEOUT}"
    )
else:
    DATABASE_URL = (
        f"mssql+pyodbc://@{host_str}/{DB_NAME}"
        f"?driver=ODBC+Driver+18+for+SQL+Server"
        f"&Trusted_Connection=yes"
        f"&TrustServerCertificate=yes"
        f"&timeout={DB_CONNECT_TIMEOUT}"
    )

_engine = None
_session_maker = None
_db_status_cache = {"available": None, "last_checked": 0.0}
STATUS_CACHE_TTL = 30.0  # seconds


def get_engine():
    global _engine, _session_maker
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=DB_CONNECT_TIMEOUT,
        )
        _session_maker = sessionmaker(bind=_engine)
    return _engine


def get_session_maker():
    global _session_maker
    if _session_maker is None:
        get_engine()
    return _session_maker


def is_database_available(force_check: bool = False) -> bool:
    """Quick cached check to see if SQL Server is responding."""
    now = time.time()
    if not force_check and _db_status_cache["available"] is not None:
        if now - _db_status_cache["last_checked"] < STATUS_CACHE_TTL:
            return bool(_db_status_cache["available"])

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_status_cache["available"] = True
        _db_status_cache["last_checked"] = now
        return True
    except Exception as e:
        logger.warning(f"SQL Server unavailable at {host_str}/{DB_NAME}: {e}")
        _db_status_cache["available"] = False
        _db_status_cache["last_checked"] = now
        return False


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager providing a database session with guaranteed closure."""
    maker = get_session_maker()
    db: Session = maker()
    try:
        yield db
    finally:
        db.close()
