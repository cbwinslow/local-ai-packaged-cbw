# RAG Pipeline

1. **Chunking**: token-aware, overlap=64; keep citation spans intact.
2. **Index**: write to Postgres (`pgvector`) and optional OpenSearch for BM25.
3. **Hybrid Retrieval**: vector + keyword + graph k-hop (entity neighborhood).
4. **Rerank**: small cross-encoder or LLM reranker for top 20→5.
5. **Answer**: compose with explicit citations and confidence.
6. **Cache**: store Q/A pairs with document versions to detect stale answers.
7. **Eval**: TruthfulQA-like sets + custom golden claims; track drift.

Document prompts and guardrails in `prompts/` with tests.
