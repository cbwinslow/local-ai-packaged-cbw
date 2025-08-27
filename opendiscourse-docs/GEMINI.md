# Gemini (Google) Setup

1. Get a Google AI Studio API key and add `GOOGLE_API_KEY` to `.env`.
2. Configure LiteLLM to recognize `gemini-1.5-pro` / `flash` routes, or call through LiteLLM's OpenAI-compatible API.
3. For long context, prefer `1.5-pro`. For fast tools, try `flash`.
4. Safety: enable harassment/medical filters as needed; log all refusal reasons.

**Embedding:** Use text-embedding-004 (via LiteLLM) or unify with your global embeddings pick.
