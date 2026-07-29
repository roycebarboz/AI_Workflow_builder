# 09 — Docker Compose one-command setup

**What to build:** A single `docker-compose.yml` at the repo root brings up frontend, backend, and Postgres together, so `docker-compose up` is the one-command local setup path for graders/users. README documents this as the primary path, with the non-Docker manual setup kept as a documented fallback.

**Blocked by:** 05 — Branch/condition nodes (core app should be feature-complete enough to be worth containerizing)

**Status:** resolved

- [x] `docker-compose.yml` defines frontend, backend, and postgres services wired together
- [x] `docker-compose up` from a clean checkout (plus `.env` populated from `.env.example`) results in a working app reachable in the browser
- [x] README's setup section leads with the Docker path, non-Docker path documented as fallback

## Comments

`backend/Dockerfile` runs `alembic upgrade head` on every container start before
`uvicorn`, so migrations never need a manual step in the Docker path. Postgres
has no published host port in Compose — only the backend needs to reach it,
over the internal Compose network — which also sidesteps colliding with any
Postgres a developer already has bound to local port 5432 (hit this during
testing against the manual-setup `aiwb-postgres` container and dropped the
mapping rather than working around it). `backend`'s `DATABASE_URL` and
`FRONTEND_ORIGIN` are overridden in `docker-compose.yml` to point at the
Compose service hostnames; everything else (`OPENAI_API_KEY`, `OPENAI_MODEL`,
`TAVILY_API_KEY`) flows through from the root `.env` via `env_file`. Frontend
is built with `vite build` and served with `vite preview --host 0.0.0.0`
rather than a dev server — no code change needed for
`VITE_API_BASE_URL`'s `http://localhost:8000` default, since the browser
reaches the backend through the host-mapped port either way.

Verified end-to-end locally: `docker-compose build` then `docker-compose up`
from a clean `.env` brings up all three containers, Postgres reports healthy,
the backend runs its migrations and serves `/health` and `/workflows`, CORS
reflects `FRONTEND_ORIGIN`, and the frontend responds on `:5173`.
