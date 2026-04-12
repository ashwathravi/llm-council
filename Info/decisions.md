# Decisions

- Keep the frontend thin and push orchestration, retrieval, storage, and export logic into the backend.
- Use OpenRouter as the model gateway and treat council/chairman models as runtime-configurable conversation settings.
- Store whole conversations as JSON blobs instead of a relational message schema.
- Support both database and filesystem storage so the app can run with or without Postgres.
- Reuse one shared `httpx.AsyncClient` for OpenRouter traffic.
- Run expensive work off the event loop where needed:
  - PDF parsing in a threadpool
  - embedding inference in a threadpool.
- Use SSE for chat so the UI can render stage-by-stage progress and token streaming.
- Require Google login + backend-issued JWT for API access, with optional email/domain allowlists.
- Add basic hardening in-process:
  - CORS allowlist
  - security headers
  - in-memory per-IP rate limiting.
- Build frontend separately and ship a single backend container that serves both API and SPA assets.
