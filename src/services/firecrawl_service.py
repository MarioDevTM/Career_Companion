import time
import hashlib
import copy
from dataclasses import dataclass, field
from typing import Optional, Any
from urllib.parse import urlsplit
import httpx

from src.config import AppConfig


@dataclass
class FirecrawlSearchResult:
    success: bool
    query: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    formatted_context: str = ""
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    cached: bool = False


class FirecrawlService:
    """
    Optional web retrieval service backed by Firecrawl.
    Handles web search failures independently from Ollama inference and treats
    all retrieved web snippets as untrusted passive reference material.
    """

    API_URL = "https://api.firecrawl.dev/v2/search"
    MAX_SNIPPET_CHARS = 900
    _cache: dict[tuple[str, int], tuple[float, FirecrawlSearchResult]] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_results: Optional[int] = None,
        cache_ttl_seconds: Optional[int] = None,
        http_client: Optional[Any] = None,
        cache: Optional[dict] = None,
    ):
        self.api_key = api_key if api_key is not None else AppConfig.get_firecrawl_api_key()
        self.timeout_seconds = timeout_seconds or AppConfig.get_firecrawl_timeout()
        self.max_results = max_results or AppConfig.get_search_max_results()
        self.cache_ttl_seconds = (
            cache_ttl_seconds if cache_ttl_seconds is not None else AppConfig.get_search_cache_ttl_seconds()
        )
        self._http_client = http_client
        self._cache = cache if cache is not None else {}

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    @staticmethod
    def _is_safe_http_url(url: str) -> bool:
        if not isinstance(url, str):
            return False
        parsed = urlsplit(url.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password

    @classmethod
    def _clean_snippet(cls, raw_text: str) -> str:
        cleaned = " ".join((raw_text or "").split())
        if len(cleaned) > cls.MAX_SNIPPET_CHARS:
            return cleaned[: cls.MAX_SNIPPET_CHARS] + " ..."
        return cleaned

    def search(self, query: str) -> FirecrawlSearchResult:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return FirecrawlSearchResult(
                success=False,
                query="",
                error_type="invalid_search_query",
                error_message="Firecrawl search query cannot be empty.",
            )

        if not self.is_configured():
            return FirecrawlSearchResult(
                success=False,
                query=cleaned_query,
                error_type="firecrawl_not_configured",
                error_message=(
                    "Firecrawl web search is not configured. Set FIRECRAWL_API_KEY in deployment secrets or .env "
                    "or switch Sources to 'My materials (no web search)'."
                ),
            )

        cache_key = (hashlib.sha256(self.api_key.encode()).hexdigest(), cleaned_query, self.max_results)
        now = time.monotonic()
        if self.cache_ttl_seconds > 0 and cache_key in self._cache:
            cached_at, cached_result = self._cache[cache_key]
            if now - cached_at <= self.cache_ttl_seconds:
                return FirecrawlSearchResult(
                    success=cached_result.success,
                    query=cached_result.query,
                    sources=copy.deepcopy(cached_result.sources),
                    formatted_context=cached_result.formatted_context,
                    error_type=cached_result.error_type,
                    error_message=cached_result.error_message,
                    cached=True,
                )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": cleaned_query[:300],
            "limit": self.max_results,
            "sources": [{"type": "web"}],
            "timeout": int(self.timeout_seconds * 1000),
        }

        try:
            if self._http_client is not None:
                response = self._http_client.post(
                    self.API_URL, json=payload, headers=headers, timeout=self.timeout_seconds
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(self.API_URL, json=payload, headers=headers)

            status_code = getattr(response, "status_code", 200)
            if status_code >= 400:
                return FirecrawlSearchResult(
                    success=False,
                    query=cleaned_query,
                    error_type={401: "firecrawl_authentication", 403: "firecrawl_authentication",
                                402: "firecrawl_credits", 429: "firecrawl_rate_limit"}.get(status_code, "firecrawl_http_error"),
                    error_message={401: "Firecrawl credentials are invalid.", 403: "Firecrawl access was denied.",
                                   402: "Firecrawl credits are exhausted. Use My materials to continue without search.",
                                   429: "Firecrawl rate limit reached. Wait before retrying or use My materials."}.get(
                                       status_code, f"Firecrawl retrieval failed (HTTP {status_code})."),
                )

            body = response.json()
            raw_items = body.get("data", []) if isinstance(body, dict) else []
            if isinstance(raw_items, dict):
                raw_items = raw_items.get("web", [])
            if not isinstance(raw_items, list):
                raw_items = []
            sources: list[dict[str, str]] = []
            context_blocks: list[str] = []

            for idx, item in enumerate(raw_items[: self.max_results], start=1):
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "").strip()
                if not self._is_safe_http_url(url):
                    continue
                title = str(item.get("title") or item.get("metadata", {}).get("title") or url).strip()
                snippet_source = (
                    item.get("markdown")
                    or item.get("description")
                    or item.get("content")
                    or item.get("snippet")
                    or ""
                )
                snippet = self._clean_snippet(str(snippet_source))
                if not any(s["url"] == url for s in sources):
                    sources.append({"title": title, "url": url, "snippet": snippet})
                    context_blocks.append(
                        f"[Web Source {idx}] Title: {title}\nURL: {url}\nExcerpt: {snippet or 'No excerpt provided.'}"
                    )

            formatted_context = "\n\n".join(context_blocks)
            result = FirecrawlSearchResult(
                success=bool(sources),
                error_type=None if sources else "firecrawl_empty",
                error_message=None if sources else "No usable web results were returned.",
                query=cleaned_query,
                sources=sources,
                formatted_context=formatted_context,
            )
            if self.cache_ttl_seconds > 0 and sources:
                expired = [k for k, (stamp, _) in self._cache.items() if now - stamp > self.cache_ttl_seconds]
                for key in expired:
                    self._cache.pop(key, None)
                while len(self._cache) >= 100:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[cache_key] = (now, result)
            return result

        except (httpx.TimeoutException, TimeoutError) as exc:
            return FirecrawlSearchResult(
                success=False,
                query=cleaned_query,
                error_type="firecrawl_timeout",
                error_message=f"Firecrawl web search timed out after {self.timeout_seconds:.0f}s.",
            )
        except (httpx.RequestError, ConnectionError) as exc:
            return FirecrawlSearchResult(
                success=False,
                query=cleaned_query,
                error_type="firecrawl_network_error",
                error_message="Firecrawl is unreachable. Try again later or use My materials.",
            )
        except Exception as exc:
            return FirecrawlSearchResult(
                success=False,
                query=cleaned_query,
                error_type="firecrawl_error",
                error_message="Firecrawl returned an unexpected response. Use My materials or try again later.",
            )
