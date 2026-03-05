# Utility & UX Improvements Roadmap

_Last updated: March 4, 2026_

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


- [x] Guided “first prompt” onboarding
  - Status: Implemented.
  - Frontend:
    - Added starter prompt quick picks in the empty conversation state.
    - Added keyboard shortcuts (`Alt+1/2/3`) to prefill starter prompts and surfaced shortcut hints in the UI.

- [x] Session templates by intent
  - Status: Implemented.
  - Frontend:
    - Added intent templates (Debug, Product, Security) to the council configuration dialog.
    - Applying a template pre-selects framework, suggested council members, and a chairman.
- [ ] Preset management enhancements
  - Add rename/delete/reorder support and optional “pin favorite preset”.

- [ ] Retry granularity improvements
  - Add per-model retry buttons and explicit retry result toasts.

- [ ] Synthesis refresh option after retry
  - Optional action to rerun Stage 2 + Stage 3 using recovered Stage 1 responses.

## Progress Log

- 2026-03-05: Added guided “first prompt” onboarding with starter prompt quick picks, Alt+1/2/3 shortcuts, and send shortcut guidance in empty-state UI.
- 2026-03-05: Added intent-based session templates in the council configuration flow (Debug/Product/Security) with one-tap application.
- 2026-03-04: Implemented retry endpoint + UI action, added comparison diff tab, and re-established roadmap tracking file.
