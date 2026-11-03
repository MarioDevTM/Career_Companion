# Web search configuration

This release uses Ollama for generation and optional Firecrawl v2 search.
It has no Gemini dependency. See DEPLOYMENT.md for current configuration.

Sources defaults to **My materials (no web search)**. Combined mode uses search
when configured and explicitly reports a fallback if retrieval fails. Web-only
mode stops on retrieval failure rather than pretending its answer is verified.
The typed request (up to 300 characters) is sent to Firecrawl; selected documents
and profile entries are not automatically included in the search query.

Retrieved snippets are untrusted reference data, and the source list contains
actual retrieval URLs. Sources do not prove every claim in a model's answer.
Search has no automatic retries; cache entries are limited to 100 per browser
session and expire according to SEARCH_CACHE_TTL_SECONDS. Set this to 0 for
fresh searches. The cache is ephemeral and cleared when signing out.
