from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from src.config import AppConfig
from src.models import Base, UserSetting


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_engine = None
_SessionLocal = None
_OLLAMA_MIGRATION_KEY = "ollama_migration_v1"


def get_engine(database_url: str | None = None):
    global _engine
    url = database_url or AppConfig.get_database_url()
    if _engine is None or str(_engine.url) != url:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)
    return _engine


def get_session_factory(database_url: str | None = None):
    global _SessionLocal
    engine = get_engine(database_url)
    if _SessionLocal is None or _SessionLocal.kw.get("bind") is not engine:
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _SessionLocal


def init_db(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    with get_db_session(database_url) as session:
        tz_setting = session.get(UserSetting, "timezone")
        if not tz_setting:
            session.add(UserSetting(key="timezone", value=AppConfig.get_default_timezone()))

        migration_setting = session.get(UserSetting, _OLLAMA_MIGRATION_KEY)
        if not migration_setting:
            # Remove obsolete provider keys if present from older versions
            for obsolete_key in ("gemini_model", "gemini_model_migration_v1", "gemini_api_key"):
                old_row = session.get(UserSetting, obsolete_key)
                if old_row is not None:
                    session.delete(old_row)

            if not session.get(UserSetting, "ollama_model"):
                session.add(UserSetting(key="ollama_model", value=AppConfig.get_ollama_model()))
            if not session.get(UserSetting, "ollama_base_url"):
                session.add(UserSetting(key="ollama_base_url", value=AppConfig.get_ollama_base_url()))

            session.add(UserSetting(key=_OLLAMA_MIGRATION_KEY, value="completed"))

        session.commit()


@contextmanager
def get_db_session(database_url: str | None = None) -> Generator[Session, None, None]:
    factory = get_session_factory(database_url)
    session: Session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_setting(session: Session, key: str, default: str = "") -> str:
    setting = session.get(UserSetting, key)
    return setting.value if setting else default


def set_setting(session: Session, key: str, value: str) -> None:
    setting = session.get(UserSetting, key)
    if setting:
        setting.value = value
    else:
        session.add(UserSetting(key=key, value=value))
    session.commit()