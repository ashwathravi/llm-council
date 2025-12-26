# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a multi-agent deliberation system where multiple LLMs collaboratively answer user questions. Features specialized council modes (Debate, Six Hats) and a 3-stage process (Initial Responses -> Peer Review/Critique -> Chairman Synthesis).

It is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Architecture

### Backend (`backend/`)

**Core Components**:

- **`config.py`**: Configuration for API keys, DB URL, and default models.
- **`main.py`**: FastAPI application entry point. Handles defined routes and middleware.
- **`council.py`**: Core logic for the 3-stage council process including distinct frameworks (`standard`, `debate`, `six_hats`, `ensemble`).
- **`openrouter.py`**: Async client for interacting with OpenRouter API using `httpx`.
- **`storage.py`**: Dual-mode persistence layer. Uses `SQLAlchemy` + `asyncpg` for PostgreSQL (if `DATABASE_URL` present) or JSON files (local default).
- **`auth.py`**: Handles Google OAuth2 verification and JWT session management.

**Key APIs**:

- `POST /api/conversations`: Create conversation with specific `council_models` and `framework`.
- `GET /api/conversations/{id}/message/stream`: SSE endpoint for streaming responses from the council.

### Frontend (`frontend/src/`)

**Tech Stack**: React, Vite, CSS Modules (Vanilla).

**Design System**:

- **Material Design 3**: Fully custom implementation using CSS variables (`design_tokens.css`).
- **Theming**: Supports dynamic color schemes (Blue/Teal) and system usage.
- **Layout**: Fixed/Sticky headers with independent scrolling content areas.

**Key Components**:

- **`App.jsx`**: Main state manager for conversation history and active chat.
- **`Sidebar.jsx`**: Handles navigation, "New Conversation" creation, and Model Selection.
- **`ChatInterface.jsx`**: Main chat view with message bubbles, input area, and council stages.
- **`ModelSelect.jsx`**: Complex multi-select dropdown for choosing specific models from OpenRouter list.
- **`Stage[1-3].jsx`**: Specialized views for each stage of the council process.

## Deployment & DevOps

**Infrastructure**:

- **Render**: Primary deployment target using `render.yaml` Blueprint.
- **Database**:
  - **Supabase**: Recommended production DB (connected via external `DATABASE_URL`).
  - **Render Managed**: Alternative via Blueprint auto-provisioning.
- **Local Dev**: Uses `./start.sh` wrapper for concurrent backend/frontend.

**Environment Variables**:

- `OPENROUTER_API_KEY`: Required for LLM access.
- `DATABASE_URL`: Connection string for Postgres (optional, falls back to files).
- `JWT_SECRET_KEY`: For session security.
- `GOOGLE_CLIENT_ID`: For OAuth (optional in dev).

## Implementation Details

### Council Modes

1. **Standard Council**: Independent answers -> Peer Ranking -> Synthesis.
2. **Chain of Debate**: Answers -> Critique logical flaws -> Synthesis.
3. **Six Thinking Hats**: Assigned perspectives (Facts, Feelings, Risks, etc.) -> Synthesis.
4. **Ensemble**: Parallel answers -> Fast synthesis (skips review).

### Storage Strategy

- **Dual Mode**: The `Storage` class checks `DATABASE_URL`.
- **Schema**: Simple relational schema (`conversations`, `messages`, `users`).
- **JSON Fallback**: Mirrors DB schema in JSON files under `data/conversations/`.

### UI/UX Rules

- **MD3 Compliance**: Use tokens from `design_tokens.css`.
- **Zero CLS**: Headers must be sticky/fixed. Content scrolls within `flex: 1` containers.
- **Vibe**: "Premium & Dynamic" - use micro-interactions and tonal surfaces.

## Common Workflows

- **Add New Mode**: Update `backend/council.py` with new prompt chain -> Add option in `Sidebar.jsx`.
- **Change Default Models**: Edit `backend/config.py`.
- **Update Styles**: Modify `design_tokens.css` for global changes, or component CSS for specific tweaks.

## Key Design Decisions

### Stage 2 Prompt Format

The Stage 2 prompt is very specific to ensure parseable output:

```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy

- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy

- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency

- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

### Async/Parallel Philosophy

- The entire flow is async/parallel where possible to minimize latency.

## Future Enhancement Ideas

- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling
- Support for multi-modal capabilities  (need to make sure the models select support it)
- Embedding models for RAG, classification, search, clustering, etc.
- Support for tool calling (need to make sure the models select support it)
- Calls to "openai/gpt-5.2-pro" not working
- Automatica sanitization before sending to LLMs (and de-sanitize after receiving using Gemini models)