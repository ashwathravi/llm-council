# Utility & UX Improvements Roadmap

_Last updated: March 5, 2026_

## Quick Wins (Execution Status)

- [x] Saved Council Presets
  - Status: Already implemented in the existing UI (`Save Config`, `Load Saved Config`, local persistence).
  - Notes: Presets are selectable from configuration dialog and can be applied before session start.

- [x] Retry Failed Model
  - Status: Implemented.
  - Backend:
    - Added `POST /api/conversations/{conversation_id}/messages/{message_index}/retry-stage1`.
    - Retries only failed Stage 1 model calls for a specific assistant message.
    - Persists merged Stage 1 results and updated error metadata without rerunning the full council flow.
  - Frontend:
    - Added per-message `Retry Failed Models` action in council error panel.
    - Updates message state in-place with recovered model outputs.

- [x] Comparison Diff
  - Status: Implemented.
  - Frontend:
    - Added `Diff` tab in council message block when at least 2 Stage 1 responses exist.
    - Includes agreement signals, pairwise similarity bars, and distinctive terms per model.

## Follow-Up Queue

- [x] Preset management enhancements
  - Status: Implemented.
  - Frontend:
    - Added preset rename, delete, reorder (up/down), and pin/unpin controls in `Load Saved Config`.
    - Presets persist pinned state and ordering in local storage.

- [x] Retry granularity improvements
  - Status: Implemented.
  - Frontend:
    - Added per-model retry buttons in the council error panel.
    - Added explicit retry result toasts for success, partial recovery, and failure.

- [x] Synthesis refresh option after retry
  - Status: Implemented.
  - Backend:
    - Extended `POST /api/conversations/{conversation_id}/messages/{message_index}/retry-stage1` with `refresh_synthesis`.
    - Supports Stage 2 + Stage 3 refresh against current/recovered Stage 1 responses.
  - Frontend:
    - Added `Refresh Synthesis` action after retries (when retry history exists).
    - Updates message Stage 2/Stage 3 in-place and surfaces refresh result via toast.

## Progress Log

- 2026-03-04: Implemented retry endpoint + UI action, added comparison diff tab, and re-established roadmap tracking file.
- 2026-03-05: Implemented preset management controls (rename/delete/reorder/pin), per-model retries with result toasts, and synthesis refresh support after retry.
