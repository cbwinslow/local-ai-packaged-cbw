# Docker Notes

- Each service must be restartable and idempotent.
- Add healthchecks for DBs and gateways.
- Consider `depends_on` + wait-for scripts for API readiness.
- Keep container logs JSON-structured for easy ingestion.
