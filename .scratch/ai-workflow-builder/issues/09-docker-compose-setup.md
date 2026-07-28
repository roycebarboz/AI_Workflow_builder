# 09 — Docker Compose one-command setup

**What to build:** A single `docker-compose.yml` at the repo root brings up frontend, backend, and Postgres together, so `docker-compose up` is the one-command local setup path for graders/users. README documents this as the primary path, with the non-Docker manual setup kept as a documented fallback.

**Blocked by:** 05 — Branch/condition nodes (core app should be feature-complete enough to be worth containerizing)

**Status:** ready-for-agent

- [ ] `docker-compose.yml` defines frontend, backend, and postgres services wired together
- [ ] `docker-compose up` from a clean checkout (plus `.env` populated from `.env.example`) results in a working app reachable in the browser
- [ ] README's setup section leads with the Docker path, non-Docker path documented as fallback
