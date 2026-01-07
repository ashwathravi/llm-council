# Feature Passport 🎫

| Metadata | Value |
| :--- | :--- |
| **Feature Name** | Support for uploading PDF files to the conversation / models |
| **Status** | `REVIEW` |
| **Priority** | P2 |
| **Assignee** | Agent |

---

## 🧠 Phase 1: Deep Planning (Human & Planner Agent)

### 1.1 Idea & Context (User Input)

**Original Issue**: [https://github.com/ashwathravi/llm-council/issues/18](https://github.com/ashwathravi/llm-council/issues/18)

### Summary

Add support for uploading PDF files to the conversation so that models can use extracted document content for context.

### Motivation

- Users frequently want to upload and reference external documents (reports, specs, research papers, contracts) in conversations.
- PDF upload streamlines workflows and enables question-answering, summarization, and citations based on uploaded content.

### Goals

- Allow one or more PDF files to be uploaded to a conversation.
- Make uploaded PDFs available for retrieval/context in conversation with the model.
- UI: Show upload progress, processing status, errors; display metadata for uploaded files.

### Non-goals

- Editable or in-app PDF modification.

### Acceptance Criteria

- Users can upload a PDF, it is processed and available for conversation context.
- Relevant content is returned by retrieval (with citation: filename and page).
- Upload/processing state is clearly indicated in the UI and errors are surfaced.

### Security, Privacy, Error Handling

- Validate file type and size. Reject encrypted or unsupported PDFs.
- Optionally scan for PII or content policy violations.
- Manage document retention per settings.
- Handle extraction failures gracefully (display error, retry option).

---

**Labels:** enhancement, backend, frontend

**Assignee:** ashwathravi

*Describe the feature here. Attach images from `.agent/assets` if needed.*

### 1.2 Requirements & Corner Cases (User Input)

- [x] PDFs are tied to a conversation; users can remove PDFs from a conversation.
- [x] Upload UI lives in the chat input area; multi-file select supported; show upload progress and processing status.
- [x] Validation: PDF only; max file size 10MB each; max 5 PDFs per conversation; reject encrypted PDFs.
- [x] Extraction is text-only; store extracted text only (do not persist PDFs).
- [x] Storage: local disk in dev; Postgres in production.
- [x] Retrieval: embeddings + vector search; include citations (filename + page) and inject context into all stages.
- [x] On extraction failure, allow retry (re-upload).
- *Corner Case*: User sends a message while docs are still processing; retrieval should ignore non-ready docs and surface status in UI.
- *Corner Case*: Extraction yields empty text (scanned PDFs); mark as failed with actionable error.
- *Corner Case*: Removing a document should remove it from future retrieval, but preserve past message history.

### 1.3 Clarification Log (Iterative)

*(Agent asks questions here, User answers)*

- **Q**: Should PDFs be tied to a conversation, and can users remove them?
- **A**: Conversation-scoped; removal allowed.
- **Q**: Upload UX details?
- **A**: In chat input area, multi-file select; show progress and status.
- **Q**: Limits and validation?
- **A**: PDF only; max 10MB each; max 5 PDFs; reject encrypted PDFs.
- **Q**: Extraction and storage?
- **A**: Text-only extraction; store extracted text only.
- **Q**: Storage target?
- **A**: Local disk for dev; Postgres for production.
- **Q**: Retrieval approach?
- **A**: Embeddings + vector search.
- **Q**: Who gets the context?
- **A**: All stages/models.
- **Q**: Failure handling?
- **A**: Allow retry on extraction failure (re-upload).

### 1.4 The Blueprint (Planner Agent)

*The finalized technical plan. To be approved by User.*

#### Files to Create/Modify

- `backend/main.py` (upload/list/delete endpoints; retrieval injection in message flow)
- `backend/storage.py` (document CRUD, chunk persistence, retrieval accessors)
- `backend/database.py` (document + chunk tables for Postgres)
- `backend/config.py` (limits, chunk sizes, embedding model config)
- `backend/documents.py` (PDF extraction, chunking, embedding, vector search helpers)
- `backend/retrieval.py` (query embedding + top-k selection + citation formatting)
- `frontend/src/api.js` (document upload/list/delete APIs with progress hook)
- `frontend/src/components/ChatInterface.jsx` (upload UI + document list + status)
- `frontend/src/components/ChatInterface.css` (upload UI styling)
- `frontend/src/components/Stage3.jsx` (render citations if returned)
- `tests/` (new unit tests for extraction + retrieval; API tests)
- `pyproject.toml` (dependencies: pypdf, sentence-transformers, numpy)

#### Milestones

*If the feature is huge, the Planner will break it down here.*

**Milestone 1: Data model and storage**

1. Add document metadata and chunk storage schemas for both Postgres and file-backed storage.
2. Persist per-document status (`processing`, `ready`, `failed`) with error details.
3. Store chunk text + embeddings with page references for citation.

**Milestone 2: Ingestion pipeline**

1. Validate PDF uploads (type, size, count, encryption).
2. Extract text per page; chunk with overlap; compute embeddings.
3. Save extracted text and embeddings; mark status and surface errors.
4. Delete PDF bytes after extraction (no persistence).

**Milestone 3: Retrieval integration**

1. Embed user query, run vector search over ready chunks for the conversation.
2. Build a retrieval context block with citations (filename + page).
3. Inject context into all stages (stage 1, stage 2 prompts, stage 3 synthesis).
4. Return citation metadata for UI display.

**Milestone 4: Frontend UX**

1. Add multi-file upload control in chat input with progress.
2. Show document list with status, metadata (filename, page count, size), and delete action.
3. Render citations for the final response (and/or inline in markdown).

**Milestone 5: Verification**

1. Unit tests for PDF extraction, chunking, and vector search.
2. API tests for upload/list/delete and retrieval path.
3. Manual UI pass: upload, failure retry, delete, and citation display.

> [!IMPORTANT]
> **Approval**:
>
> - [x] I have reviewed the Clarification Log and The Blueprint.
> - [x] I authorize the agents to Execute this plan. (Transition Status to `APPROVED`).

---

## 🏃 Phase 2: Autonomous Execution (Auto-Pilot)

*Triggers automatically when Status = `APPROVED`*

### 2.1 Architecture Review (Architect Agent)

- [x] Security/Consistency Check Passed
- *Adjustments made to Blueprint*: Added cleanup on conversation delete; retrieval failures fall back to no-context.

### 2.2 Execution Log (Implementation Agent)

#### Milestone 1

- [x] Document metadata and chunk schemas for file + Postgres storage.
- [x] Document status and error persistence.
- [x] Chunk storage with embeddings and page references.

- [x] Verification (Tests/Screenshots): `tests/test_documents.py`

#### Milestone 2

- [x] Upload validation for file type, size, count, encryption.
- [x] Text extraction + chunking + embedding pipeline.
- [x] Status updates for processing/ready/failed.

#### Milestone 3

- [x] Retrieval with embeddings and citation formatting.
- [x] Context injected into all stages.
- [x] Added server-side logging for empty/errored model responses.

#### Milestone 4

- [x] Upload UI in chat input with progress.
- [x] Document list with status, metadata, and remove action.
- [x] Citation rendering in final response.

#### Milestone 5

- [x] Unit tests for chunking and retrieval ordering.
- [x] API upload test with mocked extraction/embeddings.
- [x] Full backend test suite: `uv run pytest`

### 2.3 Final Assembly

**Outcome**: Status moved to `REVIEW`

---

## 🏁 Phase 3: Final Review (User)

- [ ] I have verified the functionality.
- [ ] Code looks good.

**Action**: Move Status to `DONE`.
