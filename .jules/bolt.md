## 2024-10-24 - [Frontend Re-render Storm]
**Learning:** The application re-renders the entire message list for every single streaming token because `App.jsx` mutates state (preventing `memo` from working even if it were there) and `ChatInterface` lacks memoization.
**Action:** Always implement immutable state updates in React, especially for streaming data, and use `React.memo` for list items in chat interfaces.

## 2025-01-02 - [Nested Component Re-renders]
**Learning:** Even with `MessageItem` memoized, its children (`Stage1`, `Stage2`, `Stage3`) were re-rendering unnecessarily during streaming updates of sibling stages. For example, during Stage 3 streaming, Stage 1 and 2 components (which are static) were re-rendering on every token because the parent `MessageItem` re-rendered.
**Action:** Memoize computational/heavy presentation components (`React.memo`) that are children of frequently updating parents, even if they seem static.

## 2025-01-08 - [Blocking Async Endpoints]
**Learning:** `async def` endpoints in FastAPI run on the main event loop. Calling synchronous CPU-bound functions (like PDF extraction/embedding) inside them blocks the entire server.
**Action:** Always wrap synchronous blocking calls in `await starlette.concurrency.run_in_threadpool(func, *args)` when using `async def`.

## 2025-05-23 - [Database Sorting Latency]
**Learning:** For sort-heavy queries (e.g., `ORDER BY created_at DESC` in `list_conversations`), PostgreSQL defaults to a Seq Scan + Sort if no suitable index exists, which is O(N log N). While execution time might be small for N=2000 (1.2ms), adding a composite index `(user_id, created_at)` enables an Index Scan Backward (0.7ms), reducing complexity to O(limit) or O(N).
**Action:** Always verify query plans for frequently accessed list endpoints and add composite indexes to avoid sort operations.
