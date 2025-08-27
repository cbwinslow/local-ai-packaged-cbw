# News Ingestion

- **Sources**: RSS/Atom, sitemaps, publisher APIs (when available).
- **Fulltext**: newspaper3k, trafilatura, or Readability; handle paywalls *legally*.
- **Normalization**: language detection, dedupe by checksum + near-dup embeddings.
- **Scheduling**: APScheduler or Celery beat. Stagger by domain.
- **Logging**: Per-article structured logs with timings, response codes, and parser paths.
