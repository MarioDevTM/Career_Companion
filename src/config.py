import os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
BACKUPS_DIR = DATA_DIR / "backups"

for directory in (DATA_DIR, UPLOADS_DIR, BACKUPS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


class AppConfig:
    DEFAULT_TIMEZONE = "Europe/Bucharest"
    DEFAULT_AI_PROVIDER = "ollama"
    DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
    DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"
    DEFAULT_OLLAMA_KEEP_ALIVE = "10m"
    DEFAULT_OLLAMA_NUM_CTX = 4096
    DEFAULT_OLLAMA_OUTPUT_TOKENS = 700
    DEFAULT_OLLAMA_TIMEOUT_MS = 120000
    SUPPORTED_DOC_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

    APPLICATION_STATUSES = [
        "Saved",
        "Applied",
        "Screening",
        "Assessment",
        "Interview",
        "Offer",
        "Accepted",
        "Rejected",
        "Withdrawn",
        "On hold",
        "No response",
    ]

    ACTIVE_STATUSES = {
        "Saved",
        "Applied",
        "Screening",
        "Assessment",
        "Interview",
        "Offer",
        "On hold",
    }

    WORK_ARRANGEMENTS = ["Remote", "Hybrid", "On-site", "Unspecified"]
    EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Freelance", "Internship"]
    PRIORITIES = ["Low", "Medium", "High"]
    PAY_PERIODS = ["Yearly", "Monthly", "Hourly", "Daily", "Unspecified"]
    TAX_DESIGNATIONS = ["Gross", "Net", "Unspecified"]
    COMPETENCY_TAGS = [
        "communication",
        "teamwork",
        "prioritization",
        "troubleshooting",
        "leadership",
        "system-design",
        "ownership",
        "stakeholder-management",
        "adaptability",
        "mentoring",
    ]

    @classmethod
    def get_database_url(cls) -> str:
        default_db = f"sqlite:///{(DATA_DIR / 'career_companion.db').as_posix()}"
        return os.getenv("DATABASE_URL", default_db)

    @classmethod
    def get_ai_provider(cls) -> str:
        return os.getenv("AI_PROVIDER", cls.DEFAULT_AI_PROVIDER).strip().lower() or cls.DEFAULT_AI_PROVIDER

    @classmethod
    def get_ollama_base_url(cls) -> str:
        url = os.getenv("OLLAMA_BASE_URL", cls.DEFAULT_OLLAMA_BASE_URL).strip() or cls.DEFAULT_OLLAMA_BASE_URL
        return url.rstrip("/")

    @classmethod
    def get_ollama_model(cls) -> str:
        return os.getenv("OLLAMA_MODEL", cls.DEFAULT_OLLAMA_MODEL).strip() or cls.DEFAULT_OLLAMA_MODEL

    @classmethod
    def get_ollama_keep_alive(cls) -> str:
        return os.getenv("OLLAMA_KEEP_ALIVE", cls.DEFAULT_OLLAMA_KEEP_ALIVE).strip() or cls.DEFAULT_OLLAMA_KEEP_ALIVE

    @classmethod
    def get_ollama_num_ctx(cls) -> int:
        try:
            val = int(os.getenv("OLLAMA_NUM_CTX", str(cls.DEFAULT_OLLAMA_NUM_CTX)))
        except ValueError:
            val = cls.DEFAULT_OLLAMA_NUM_CTX
        return max(1024, val)

    @classmethod
    def get_ollama_output_tokens(cls) -> int:
        try:
            val = int(os.getenv("OLLAMA_OUTPUT_TOKENS", str(cls.DEFAULT_OLLAMA_OUTPUT_TOKENS)))
        except ValueError:
            val = cls.DEFAULT_OLLAMA_OUTPUT_TOKENS
        return max(128, val)

    @classmethod
    def get_ollama_timeout_ms(cls) -> int:
        raw_ms = os.getenv("OLLAMA_TIMEOUT_MS", "").strip()
        if raw_ms:
            try:
                return max(5000, int(raw_ms))
            except ValueError:
                pass
        raw_first = os.getenv("OLLAMA_FIRST_TIMEOUT", "").strip()
        if raw_first:
            try:
                return max(5000, int(float(raw_first) * 1000))
            except ValueError:
                pass
        return cls.DEFAULT_OLLAMA_TIMEOUT_MS

    @classmethod
    def get_ollama_connect_timeout(cls) -> float:
        try:
            return max(1.0, float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "5")))
        except ValueError:
            return 5.0

    @classmethod
    def get_ollama_read_timeout(cls) -> float:
        return max(5.0, cls.get_ollama_timeout_ms() / 1000.0)

    @classmethod
    def get_ollama_total_timeout(cls) -> float:
        try:
            total = float(os.getenv("OLLAMA_TOTAL_TIMEOUT", "300"))
            return max(cls.get_ollama_read_timeout(), total)
        except ValueError:
            return max(cls.get_ollama_read_timeout(), 300.0)

    @classmethod
    def get_firecrawl_api_key(cls) -> str | None:
        key = os.getenv("FIRECRAWL_API_KEY", "").strip()
        placeholders = {
            "",
            "your_firecrawl_api_key_here",
            "YOUR_FIRECRAWL_API_KEY",
            "replace_me",
        }
        if key in placeholders:
            return None
        return key

    @classmethod
    def get_firecrawl_timeout(cls) -> float:
        try:
            return max(5.0, float(os.getenv("FIRECRAWL_TIMEOUT", "30")))
        except ValueError:
            return 30.0

    @classmethod
    def get_search_max_results(cls) -> int:
        try:
            return max(1, min(10, int(os.getenv("SEARCH_MAX_RESULTS", "3"))))
        except ValueError:
            return 3

    @classmethod
    def get_search_cache_ttl_seconds(cls) -> int:
        try:
            return max(0, int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "3600")))
        except ValueError:
            return 3600

    @classmethod
    def get_default_timezone(cls) -> str:
        tz_name = os.getenv("APP_TIMEZONE", cls.DEFAULT_TIMEZONE).strip()
        try:
            ZoneInfo(tz_name)
            return tz_name
        except ZoneInfoNotFoundError:
            return cls.DEFAULT_TIMEZONE

    @classmethod
    def get_max_upload_bytes(cls) -> int:
        try:
            mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
        except ValueError:
            mb = 15
        return max(1, mb) * 1024 * 1024

    @classmethod
    def get_max_context_chars(cls) -> int:
        try:
            chars = int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
        except ValueError:
            chars = 6000
        # Keep context proportional to the 0.5B model's context window
        ctx_char_cap = cls.get_ollama_num_ctx() * 2
        return max(1500, min(chars, ctx_char_cap))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_dt_in_tz(dt: datetime | None, tz_name: str = "Europe/Bucharest", fmt: str = "%Y-%m-%d %H:%M %Z") -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Europe/Bucharest")
    return dt.astimezone(tz).strftime(fmt)