# Open Questions

- Is Postgres the intended production default, or is filesystem mode still a supported long-term deployment mode?
- Is storing full message history as one JSON column per conversation acceptable as conversations grow, or should messages move to a separate table?
- Should the frontend auth provider keep the current hard-coded test user bootstrap, or be aligned with the JWT-backed backend flow?
- Are OpenRouter model discovery and the `"tools"` filter still the intended way to populate selectable council models?
- How large can document corpora grow before in-process embedding retrieval and JSON-stored embeddings become a bottleneck?
- Should rate limiting remain in-memory per process, or move to a shared store for multi-instance deployments?
