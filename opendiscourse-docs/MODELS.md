# Model Access via LiteLLM

Use [LiteLLM](https://github.com/BerriAI/litellm) as the single gateway for all models (OpenAI, Gemini, Qwen, Mistral, Meta, Groq, etc.).

- Point SDKs to `${LITELLM_BASE_URL}/v1`
- Set provider keys as env vars (see `.env.example`).
- Use **one** embeddings model for consistency across corpora, unless a migration plan is documented.

Per-provider notes: see `GEMINI.md`, `QWEN.md`, `MISTRAL.md`, `LLAMA.md`, `GPT.md`.
