# Llama (Meta) & Local Runtimes

Use local runtimes (Ollama / vLLM) for private workloads. Configure the LiteLLM gateway to proxy to localhost.

- For Ollama: set `OLLAMA_HOST=http://ollama:11434`
- For vLLM: expose OpenAI-compatible API and route via LiteLLM
- Evaluate models: Llama 3.1 8B/70B, Phi-3-medium, Qwen2.5.
