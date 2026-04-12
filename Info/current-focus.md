# Current Focus

- Core implemented path is:
  - create conversation
  - send prompt
  - run council pipeline
  - stream updates to the UI
  - persist the finished assistant turn.
- Document upload, chunking, embedding, and retrieval are implemented and integrated into both sync and streaming council runs.
- Retry support exists for failed Stage 1 model calls, with optional rerun of later stages.
- Export exists for Markdown and PDF conversation downloads.
- Frontend work is centered on the chat workspace, council configuration, conversation navigation, and stage-by-stage rendering.
- The real backend auth flow exists, but the current frontend auth provider initializes with a hard-coded test user before login, so the UI does not strictly enforce real authentication state on first load.
