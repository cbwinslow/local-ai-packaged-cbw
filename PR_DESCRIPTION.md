Feature branch: feat/traefik-realtime-functions

Summary
-------
Add Traefik overlay routers for Supabase Realtime and Edge Functions; harden `.env` generation; add Hetzner deploy helper and systemd unit; add comprehensive smoke/integration tests (storage, functions, realtime, pgvector) and a DB init SQL & helper to apply it; documentation and examples for production deployment.

What
----
- Traefik overlay routers and labels to expose Realtime (port 4000) and Edge Functions (port 54321).
- `.env` generation improvements: `scripts/gen_all_in_one_env.py` includes additional LONG_KEYS and creates timestamped backups.
- Hetzner deployment helper (`scripts/deploy_hetzner.sh`) that installs Docker, initializes submodules, secures `.env`, and sets up a `systemd` unit `local-ai-packaged.service`.
- DB init SQL (local file in `supabase/docker/volumes/db/init/001_smoke_realtime.sql`) creates `public.smoke_realtime` and a trigger that sends `pg_notify` to `smoke_channel`.
- `scripts/apply_db_init_to_container.sh` to copy and execute init SQL into a running `supabase-db` container (fallback if submodule not merged).
- Tests: `scripts/tests/` (env check, compose config, pgvector, storage, functions, realtime websocket, advanced postgres LISTEN/NOTIFY) and `run_all.sh` runner.
- Documentation updates: `DEPLOY_HETZNER.md`, `.env.production.example` and various README and proxy docs updated.

Why
---
Provide production-ready routing and TLS for Realtime & Functions, ensure safe secret generation and `.env` handling, and provide repeatable deployment to Hetzner with tests to validate critical services.

Testing
-------
1. Validate compose config locally:
   ```bash
   docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml config
   ```
2. Deploy on Hetzner (ensure `CLOUDFLARE_API_TOKEN` and `BASE_DOMAIN` are set) and check `docker ps` and Traefik logs.
3. Apply DB init SQL if required:
   ```bash
   ./scripts/apply_db_init_to_container.sh supabase-db ./supabase/docker/volumes/db/init
   ```
4. Run tests:
   ```bash
   chmod +x scripts/tests/*.sh scripts/tests/*.py
   ./scripts/tests/run_all.sh
   ```

Follow-ups
----------
1. Commit `001_smoke_realtime.sql` into the `supabase` submodule (created as a separate branch & PR). The file currently exists on disk but submodule requires its own commit.
2. Merge parent repo PR and then merge submodule PR or update the submodule ref in the parent repo to the new commit.
3. After deployment, iterate on DB role hardening (user requested: "one dominant role per service").

Notes
-----
- `supabase` is a git submodule; changes inside require committing to that submodule repository and updating the parent repo's pointer.
- PR creation via API requires a GitHub token with `repo` scope (or use `gh` CLI locally).

Change checklist for reviewers
----------------------------
- [ ] Traefik routers and TLS cert issuance verified in Traefik logs
- [ ] `.env` generator covers all placeholders and backups created
- [ ] Deploy script initializes submodules and sets secure permissions on `.env`
- [ ] Tests run and either pass or have tracked issues for failures
- [ ] DB init SQL included in submodule or applied via helper

