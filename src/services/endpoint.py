"""Only administrator-configured destinations can receive inference credentials."""
import ipaddress
from urllib.parse import urlsplit
from src.config import AppConfig, setting, is_cloud


def validate_endpoint(url: str) -> str | None:
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        _ = parts.port
    except ValueError:
        return "OLLAMA_BASE_URL is not a valid URL."
    if parts.scheme not in {"http", "https"} or not host or parts.username or parts.password or parts.query or parts.fragment:
        return "Use an HTTP(S) Ollama base URL without embedded credentials, query parameters, or fragments."
    local = host.lower() == "localhost"
    try:
        address = ipaddress.ip_address(host)
        local = local or address.is_loopback
        if not local and not address.is_global:
            return "Use a public HTTPS hostname for remote Ollama, or loopback for local development."
    except ValueError:
        pass
    if local:
        if is_cloud():
            return "Cloud mode cannot use localhost. Configure an authenticated HTTPS Ollama endpoint in deployment secrets."
        return None
    if parts.scheme != "https":
        return "Remote Ollama endpoints require HTTPS."
    if not setting("OLLAMA_API_KEY").strip():
        return "Remote Ollama requires OLLAMA_API_KEY for your proxy's Bearer authentication."
    configured = AppConfig.get_ollama_base_url()
    if url.rstrip("/") != configured.rstrip("/"):
        return "Remote endpoint must match OLLAMA_BASE_URL in deployment secrets/environment; saved settings cannot redirect credentials."
    return None


def auth_headers(url: str) -> dict[str, str]:
    # Validation must run before use. Local endpoints never receive remote credentials.
    parts = urlsplit(url)
    local = parts.hostname in {"localhost", "127.0.0.1", "::1"}
    try:
        local = local or ipaddress.ip_address(parts.hostname).is_loopback
    except ValueError:
        pass
    if local:
        return {}
    key = setting("OLLAMA_API_KEY").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}
