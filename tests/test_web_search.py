from pydantic import BaseModel
from src.services.firecrawl_service import FirecrawlService
from src.services.ollama_service import OllamaService
from tests.test_ollama_service import FakeOllamaHTTPClient, FakeHTTPResponse


def setup_function():
    FirecrawlService.clear_cache()


def test_firecrawl_search_and_ollama_grounding():
    firecrawl_http = FakeOllamaHTTPClient(
        post_responses=[
            FakeHTTPResponse(
                200,
                {
                    "success": True,
                    "data": [
                        {
                            "title": "Python 3 Documentation",
                            "url": "https://docs.python.org/3/",
                            "markdown": "Official Python 3 reference documentation.",
                        },
                        {
                            "title": "Unsafe link",
                            "url": "javascript:alert(1)",
                            "markdown": "Should be ignored.",
                        },
                    ],
                },
            )
        ]
    )
    ollama_http = FakeOllamaHTTPClient(
        post_responses=[
            FakeHTTPResponse(
                200,
                {
                    "message": {"content": "Verified answer using Python docs."},
                    "done": True,
                },
            )
        ]
    )
    fc = FirecrawlService(api_key="fc-test-key", http_client=firecrawl_http, cache_ttl_seconds=0)
    service = OllamaService(http_client=ollama_http, firecrawl_service=fc)

    result = service.generate_text("Check Python docs", web_search=True)
    assert result.success is True
    assert result.search_used is True
    assert len(result.web_sources) == 1
    assert result.web_sources[0]["url"] == "https://docs.python.org/3/"
    assert "docs.python.org" in OllamaService.grounding_markdown(result)


def test_firecrawl_failure_in_web_only_mode_reports_firecrawl_error_without_calling_ollama():
    firecrawl_http = FakeOllamaHTTPClient(
        post_responses=[FakeHTTPResponse(401, {"error": "Unauthorized"})]
    )
    ollama_http = FakeOllamaHTTPClient(post_responses=[])
    fc = FirecrawlService(api_key="fc-invalid", http_client=firecrawl_http, cache_ttl_seconds=0)
    service = OllamaService(http_client=ollama_http, firecrawl_service=fc)

    result = service.generate_text("Search latest news", web_search=True, require_web_only=True)
    assert result.success is False
    assert result.error_type == "firecrawl_authentication"
    assert len(ollama_http.post_calls) == 0


def test_firecrawl_failure_in_combined_mode_falls_back_to_local_context_with_notice():
    class SimpleSchema(BaseModel):
        summary: str

    firecrawl_http = FakeOllamaHTTPClient(
        post_responses=[FakeHTTPResponse(503, {"error": "Service down"})]
    )
    ollama_http = FakeOllamaHTTPClient(
        post_responses=[
            FakeHTTPResponse(200, {"message": {"content": '{"summary": "Local summary"}'}, "done": True})
        ]
    )
    fc = FirecrawlService(api_key="fc-key", http_client=firecrawl_http, cache_ttl_seconds=0)
    service = OllamaService(http_client=ollama_http, firecrawl_service=fc)

    result = service.generate_structured(
        "Summarize",
        SimpleSchema,
        context_sections=[{"label": "Local Note", "content": "Important local fact"}],
        web_search=True,
        require_web_only=False,
    )
    assert result.success is True
    assert result.structured_data.summary == "Local summary"
    assert result.search_used is False
    assert result.search_error is not None
    assert "Answered using local materials only" in OllamaService.grounding_markdown(result)
