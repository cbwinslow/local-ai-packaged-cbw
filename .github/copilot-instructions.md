# ------------------------------------------------------------------------------
# File: COPILOT-AGENTS.yml
# Author: Blaine Winslow (cbwinslow) / ChatGPT (GPT-5 Thinking)
# Date: 2025-08-27
# Summary: Declarative manifest of available MCP servers & LLM providers.
#          Prefers FREE/LOCAL providers for codegen/review:
#            1) Local Ollama (Qwen-Coder / DeepSeek if pulled)
#            2) OpenRouter (free-tier capable models e.g., deepseek-r1)
#            3) Optional direct Qwen endpoints (if configured)
#
# Security: Never commit secrets. Use env vars or secret stores.
# ------------------------------------------------------------------------------

version: "1.1"

defaults:
  connection_timeout_s: 8
  request_timeout_s: 60
  retry:
    attempts: 2
    backoff_s: 2

env_map:
  # Generic secrets / tokens
  BITWARDEN_SESSION: "BW_SESSION"
  GITHUB_TOKEN: "GITHUB_TOKEN"
  NPM_TOKEN: "NPM_TOKEN"

  # Model providers
  OLLAMA_HOST: "OLLAMA_HOST"              # e.g., http://127.0.0.1:11434
  OPENROUTER_API_KEY: "OPENROUTER_API_KEY"
  QWEN_API_KEY: "QWEN_API_KEY"            # optional, if using direct Qwen cloud

  # RAG/DB
  POSTGRES_URL: "POSTGRES_URL"
  QDRANT_URL: "QDRANT_URL"
  WEAVIATE_URL: "WEAVIATE_URL"

# -------------------------
# Core review/lint/doc MCPs
# -------------------------
servers:

  - id: mcp-lint
    role: "Linting & style enforcement"
    url: "http://localhost:7010"
    health: "/health"
    capabilities:
      - python:black,flake8,isort
      - javascript:eslint,prettier
      - shell:shellcheck,shfmt
      - yaml:yamllint
    policies:
      fail_on: [syntax_error]
      warn_on: ["cyclomatic_complexity>10", long_function]

  - id: mcp-review
    role: "Static analysis & secure code review"
    url: "http://localhost:7011"
    health: "/health"
    capabilities:
      - python:bandit
      - multi:semgrep
    policies:
      require_checklist: [security, performance, readability, tests]
      block_merge_on_findings: true

  - id: mcp-docs
    role: "Docs & API spec generation"
    url: "http://localhost:7012"
    health: "/health"
    capabilities: [mkdocs, sphinx, openapi, typedoc]

  - id: mcp-secrets
    role: "Secrets retrieval (Bitwarden preferred)"
    url: "http://localhost:7013"
    health: "/health"
    capabilities: [bitwarden]
    required_env: [BITWARDEN_SESSION]

  - id: mcp-ci
    role: "CI/CD orchestration"
    url: "http://localhost:7014"
    health: "/health"
    capabilities: [github_actions, docker_build, terraform_plan_apply]

  - id: mcp-rag
    role: "RAG: vector search over project knowledge"
    url: "http://localhost:7015"
    health: "/health"
    capabilities:
      - embeddings: pgvector|qdrant|weaviate
      - retrieval: codebase, docs, ADRs
    notes: "Prefer local embeddings; fall back to cloud if allowed."

# -------------------------
# Code generation MCPs with FREE-FIRST routing
# -------------------------

  # 1) LOCAL FIRST: Ollama (no API cost; runs on your GPU/CPU)
  - id: mcp-codegen-ollama
    role: "Primary codegen via local Ollama"
    url: "${OLLAMA_HOST:-http://127.0.0.1:11434}"
    health: "/api/tags"
    capabilities:
      # Recommend pulling these models locally (examples):
      #   ollama pull qwen2.5-coder:7b
      #   ollama pull deepseek-r1:latest   # if available in your setup
      - models:
          preferred:
            - qwen2.5-coder:7b
            - qwen2.5-coder:14b
            - deepseek-r1:latest
          fallbacks:
            - qwen2.5-coder:3b
            - qwen2.5:7b
      - features: [tools, json_mode, streaming]
    policies:
      temperature: 0.2
      max_tokens: 2048
      stop_on:
        - "```"
      routing_weight: 80   # prefer this provider

  # 2) OpenRouter (free-tier friendly; bring your OPENROUTER_API_KEY)
  - id: mcp-codegen-openrouter
    role: "Secondary codegen via OpenRouter (free-tier models)"
    url: "https://openrouter.ai/api/v1"
    health: "/models"
    required_env: [OPENROUTER_API_KEY]
    headers:
      Authorization: "Bearer ${OPENROUTER_API_KEY}"
    capabilities:
      - models:
          preferred:
            - deepseek/deepseek-r1           # free/low-cost reasoning model
            - qwen/qwen-2.5-coder            # Qwen Coder via OpenRouter
          fallbacks:
            - qwen/qwen2.5:latest
            - deepseek/deepseek-coder
      - features: [tools, json_mode, streaming]
    policies:
      temperature: 0.2
      max_tokens: 2048
      rate_limit_strategy: "respect-provider"
      routing_weight: 15

  # 3) Optional: Direct Qwen cloud route (if you have an API key)
  - id: mcp-codegen-qwen
    role: "Tertiary codegen via Qwen cloud (optional)"
    url: "https://api.qwen.ai/v1"
    health: "/models"
    required_env: [QWEN_API_KEY]
    headers:
      Authorization: "Bearer ${QWEN_API_KEY}"
    capabilities:
      - models:
          preferred:
            - qwen2.5-coder-7b-instruct
            - qwen2.5-coder-32b-instruct
          fallbacks:
            - qwen2.5-instruct
      - features: [tools, json_mode, streaming]
    policies:
      temperature: 0.2
      max_tokens: 2048
      routing_weight: 5

# -------------------------
# Routing Guidance for Copilot/MCP clients
# -------------------------
routing:
  code_generation:
    order: [mcp-codegen-ollama, mcp-codegen-openrouter, mcp-codegen-qwen]
    safety:
      redact_secrets: true
      refuse_on_pii: false
    prompts:
      # Short system prompt appended to user prompts for consistency
      system: >
        You are a precise, security-conscious coding assistant. Prefer local
        models (Ollama) and free-tier routes (OpenRouter DeepSeek/Qwen) before
        any paid usage. Always produce safe, testable, documented code with
        clear failure handling and explicit assumptions. When unsure, ask.

  code_review:
    order: [mcp-review, mcp-lint, mcp-codegen-ollama, mcp-codegen-openrouter]
    require_checklist: [security, tests, performance, readability]

  docs_updates:
    order: [mcp-docs, mcp-rag, mcp-codegen-ollama, mcp-codegen-openrouter]

# -------------------------
# Health Checks (optional)
# -------------------------
health_checks:
  interval_s: 30
  expect:
    - mcp-lint
    - mcp-review
    - mcp-docs
    - mcp-secrets
    - mcp-ci
    - mcp-rag
    - mcp-codegen-ollama
    - mcp-codegen-openrouter
