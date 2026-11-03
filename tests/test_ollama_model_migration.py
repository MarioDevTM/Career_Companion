from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database import get_db_session, get_setting, init_db
from src.models import Base, UserSetting


def test_legacy_settings_are_cleaned_and_ollama_defaults_seeded(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(UserSetting(key="gemini_model", value="gemini-2.5-flash"))
        session.commit()
    engine.dispose()

    init_db(database_url)
    with get_db_session(database_url) as session:
        assert session.get(UserSetting, "gemini_model") is None
        assert get_setting(session, "ollama_model") == "qwen2.5:0.5b"
        assert get_setting(session, "ollama_base_url") == "http://localhost:11434"