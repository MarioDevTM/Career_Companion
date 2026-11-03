import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base
from src.config import UPLOADS_DIR


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    """Provides an isolated SQLite database session and temporary uploads directory per test."""
    test_uploads = tmp_path / "uploads"
    test_uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.config.UPLOADS_DIR", test_uploads)
    monkeypatch.setattr("src.services.document_service.UPLOADS_DIR", test_uploads)
    monkeypatch.setattr("src.services.backup_service.UPLOADS_DIR", test_uploads)

    db_file = tmp_path / "test_career.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def local_test_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("AI_PROVIDER", "ollama")
