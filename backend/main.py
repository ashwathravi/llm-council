"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import os
import io
import time
import logging
from contextlib import asynccontextmanager

from . import storage, auth, openrouter, security, documents, retrieval, config, image_artifacts, code_artifacts
from .code_execution import build_execution_context_block, run_code_execution_loop
from .database import init_db
from .council import (
    run_full_council, generate_conversation_title,
    stage1_collect_responses, stage1_collect_responses_six_hats,
    stage2_collect_rankings, stage2_collect_critiques,
    stage3_synthesize_final, calculate_aggregate_rankings, calculate_aggregate_rubrics,
    extract_visual_findings_from_response, resolve_active_models,
    build_model_weight_profile, apply_round_to_model_profiles, serialize_model_weight_profile
)
from . import export
from .session_context import (
    ALLOWED_ARTIFACT_KINDS,
    ALLOWED_ARTIFACT_SOURCES,
    ALLOWED_ARTIFACT_STATUSES,
    ALLOWED_EXECUTION_MODES,
    ALLOWED_SESSION_TYPES,
    DEFAULT_EXECUTION_MODE,
    DEFAULT_SESSION_TYPE,
    build_primary_artifact_from_document,
    build_session_context_block,
    merge_context_blocks,
    normalize_execution_mode,
    normalize_primary_artifacts,
    normalize_session_type,
)
from .session_templates import get_template_label

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (create tables) on startup
    await init_db()
    # Initialize shared HTTP client
    await openrouter.init_client()
    yield
    # Close shared HTTP client
    await openrouter.close_client()

app = FastAPI(title="LLM Council API", lifespan=lifespan)
app.mount(
    "/artifact-files",
    StaticFiles(directory=str(image_artifacts.ensure_artifact_files_dir())),
    name="artifact-files",
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content-Security-Policy
    # Allow scripts from self, inline (needed for React/Vite), and Google Auth
    # Allow images from self, data URIs, and Google user content (avatars)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://*.googleusercontent.com; "
        "connect-src 'self' https://accounts.google.com; "
        "frame-src 'self' https://accounts.google.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

# Enable CORS with configurable origins and hardened settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    framework: str = "standard"
    session_type: str = DEFAULT_SESSION_TYPE
    specialist_template_id: Optional[str] = Field(None, max_length=120)
    execution_mode: str = DEFAULT_EXECUTION_MODE
    council_models: List[str] = Field(default=[], max_length=10)
    chairman_model: Optional[str] = Field(None, max_length=100)
    primary_artifacts: List["PrimaryArtifactMetadata"] = Field(default_factory=list, max_length=10)

    @field_validator("framework")
    @classmethod
    def validate_framework(cls, v: str) -> str:
        allowed = {"standard", "six_hats", "debate", "ensemble", "heterogeneous"}
        if v not in allowed:
            raise ValueError(f"Framework must be one of: {', '.join(allowed)}")
        return v

    @field_validator("session_type")
    @classmethod
    def validate_session_type(cls, v: str) -> str:
        if v not in ALLOWED_SESSION_TYPES:
            raise ValueError(f"Session type must be one of: {', '.join(sorted(ALLOWED_SESSION_TYPES))}")
        return v

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ALLOWED_EXECUTION_MODES:
            raise ValueError(f"Execution mode must be one of: {', '.join(sorted(ALLOWED_EXECUTION_MODES))}")
        return v

    @field_validator("council_models")
    @classmethod
    def validate_council_models(cls, v: List[str]) -> List[str]:
        if len(v) > 10:
            raise ValueError("Too many models selected (max 10)")
        for model in v:
            if len(model) > 100:
                raise ValueError("Model name too long")
        return v

    @model_validator(mode="after")
    def validate_execution_mode_scope(self) -> "CreateConversationRequest":
        if self.session_type != "code_review" and self.execution_mode != DEFAULT_EXECUTION_MODE:
            raise ValueError("Execution mode is only available for code review sessions.")
        return self


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str = Field(..., max_length=50000)

class RetryStage1Request(BaseModel):
    """Request to retry failed Stage 1 models for an existing assistant message."""
    models: List[str] = Field(default_factory=list, max_length=10)
    refresh_synthesis: bool = False

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: List[str]) -> List[str]:
        if len(v) > 10:
            raise ValueError("Too many models selected (max 10)")
        for model in v:
            if len(model) > 100:
                raise ValueError("Model name too long")
        return v


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    framework: str = "standard"
    session_type: str = DEFAULT_SESSION_TYPE
    specialist_template_id: Optional[str] = None
    execution_mode: str = DEFAULT_EXECUTION_MODE
    primary_artifact_count: int = 0


class PrimaryArtifactMetadata(BaseModel):
    id: Optional[str] = Field(None, max_length=200)
    kind: str = Field(default="note", max_length=40)
    label: str = Field(..., max_length=160)
    source: str = Field(default="manual", max_length=40)
    status: str = Field(default="ready", max_length=40)
    document_id: Optional[str] = Field(None, max_length=100)
    filename: Optional[str] = Field(None, max_length=255)
    mime_type: Optional[str] = Field(None, max_length=120)
    size_bytes: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    line_count: Optional[int] = Field(None, ge=0)
    summary: Optional[str] = Field(None, max_length=500)
    preview_url: Optional[str] = Field(None, max_length=500)
    storage_path: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = Field(None, max_length=80)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in ALLOWED_ARTIFACT_KINDS:
            raise ValueError(f"Artifact kind must be one of: {', '.join(sorted(ALLOWED_ARTIFACT_KINDS))}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in ALLOWED_ARTIFACT_SOURCES:
            raise ValueError(f"Artifact source must be one of: {', '.join(sorted(ALLOWED_ARTIFACT_SOURCES))}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ALLOWED_ARTIFACT_STATUSES:
            raise ValueError(f"Artifact status must be one of: {', '.join(sorted(ALLOWED_ARTIFACT_STATUSES))}")
        return v


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    framework: str = "standard"
    session_type: str = DEFAULT_SESSION_TYPE
    specialist_template_id: Optional[str] = None
    execution_mode: str = DEFAULT_EXECUTION_MODE
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None
    primary_artifacts: List[PrimaryArtifactMetadata] = Field(default_factory=list)
    messages: List[Dict[str, Any]]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class AuthConfigResponse(BaseModel):
    google_client_id: Optional[str] = None

class DocumentMetadata(BaseModel):
    id: str
    conversation_id: str
    filename: str
    size_bytes: int
    status: str
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DocumentUploadError(BaseModel):
    filename: str
    error: str

class DocumentUploadResponse(BaseModel):
    documents: List[DocumentMetadata]
    errors: List[DocumentUploadError] = []


class ImageArtifactUploadResponse(BaseModel):
    artifacts: List[PrimaryArtifactMetadata]
    errors: List[DocumentUploadError] = []


class CodeArtifactUploadResponse(BaseModel):
    artifacts: List[PrimaryArtifactMetadata]
    errors: List[DocumentUploadError] = []


CreateConversationRequest.model_rebuild()


def _build_effective_context(
    conversation: Dict[str, Any],
    retrieval_context: Optional[str],
) -> str:
    session_context = build_session_context_block(
        conversation.get("session_type"),
        conversation.get("specialist_template_id"),
        conversation.get("primary_artifacts"),
    )
    return merge_context_blocks(session_context, retrieval_context)


async def _run_code_execution_for_conversation(
    conversation: Dict[str, Any],
    *,
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    retrieval_context: Optional[str],
    chairman_model: Optional[str],
) -> Dict[str, Any]:
    return await run_code_execution_loop(
        session_type=conversation.get("session_type"),
        execution_mode=conversation.get("execution_mode"),
        user_query=user_query,
        stage1_results=stage1_results,
        stage2_results=stage2_results,
        chairman_model=chairman_model,
        primary_artifacts=conversation.get("primary_artifacts"),
        retrieval_context=retrieval_context,
    )


def _get_ready_image_artifacts(primary_artifacts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    artifacts = []
    for artifact in normalize_primary_artifacts(list(primary_artifacts or [])):
        if artifact.get("kind") != "image":
            continue
        if artifact.get("status") != "ready":
            continue
        if not artifact.get("storage_path") or not artifact.get("mime_type"):
            continue
        artifacts.append(artifact)
    return artifacts


def _get_ready_code_artifacts(primary_artifacts: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    artifacts = []
    for artifact in normalize_primary_artifacts(list(primary_artifacts or [])):
        if artifact.get("kind") != "code":
            continue
        if artifact.get("status") != "ready":
            continue
        if not artifact.get("storage_path"):
            continue
        artifacts.append(artifact)
    return artifacts


def _get_file_backed_artifact_paths(primary_artifacts: Optional[List[Dict[str, Any]]]) -> List[str]:
    paths: List[str] = []
    for artifact in normalize_primary_artifacts(list(primary_artifacts or [])):
        storage_path = artifact.get("storage_path")
        if isinstance(storage_path, str) and storage_path.strip():
            paths.append(storage_path.strip())
    return paths


def _build_user_message_content(conversation: Dict[str, Any], user_text: str) -> Any:
    if normalize_session_type(conversation.get("session_type")) != "visual_review":
        return user_text

    message_parts: List[Dict[str, Any]] = [{"type": "text", "text": user_text}]
    for artifact in _get_ready_image_artifacts(conversation.get("primary_artifacts")):
        try:
            data_url = image_artifacts.load_image_as_data_url(
                artifact["storage_path"],
                artifact["mime_type"],
            )
        except Exception:
            logger.warning(
                "Failed to load image artifact for model input",
                extra={"artifact_id": artifact.get("id"), "conversation_id": conversation.get("id")},
            )
            continue

        message_parts.append({
            "type": "image_url",
            "image_url": {"url": data_url},
        })

    return message_parts if len(message_parts) > 1 else user_text


def _build_conversation_history(
    conversation: Dict[str, Any],
    current_user_text: str,
) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for msg in conversation.get("messages", []):
        if msg.get("role") == "user":
            history.append({"role": "user", "content": msg.get("content", "")})
        elif msg.get("role") == "assistant":
            stage3 = msg.get("stage3")
            if isinstance(stage3, dict) and stage3.get("response"):
                history.append({"role": "assistant", "content": stage3["response"]})

    history.append({
        "role": "user",
        "content": _build_user_message_content(conversation, current_user_text),
    })
    return history


def _resolve_stage1_models_for_conversation(conversation: Dict[str, Any]) -> tuple[List[str], List[str], List[str]]:
    requested_council_models = list(conversation.get("council_models") or [])
    effective_council_models = resolve_active_models(conversation.get("council_models"))
    excluded_non_vision_models: List[str] = []

    if normalize_session_type(conversation.get("session_type")) == "visual_review":
        excluded_non_vision_models = [
            model_id
            for model_id in effective_council_models
            if not openrouter.supports_vision_model(model_id)
        ]
        effective_council_models = [
            model_id
            for model_id in effective_council_models
            if openrouter.supports_vision_model(model_id)
        ]

    return requested_council_models, effective_council_models, excluded_non_vision_models


def _visual_review_requires_vision_models(conversation: Dict[str, Any], effective_models: List[str]) -> None:
    if normalize_session_type(conversation.get("session_type")) == "visual_review" and not effective_models:
        raise HTTPException(
            status_code=400,
            detail="Visual Review sessions require at least one vision-capable council model.",
        )


async def _build_code_review_artifact_context(conversation: Dict[str, Any]) -> str:
    if normalize_session_type(conversation.get("session_type")) != "code_review":
        return ""

    sections: List[str] = []
    for artifact in _get_ready_code_artifacts(conversation.get("primary_artifacts")):
        try:
            content = await run_in_threadpool(code_artifacts.load_code_file, artifact["storage_path"])
        except Exception:
            logger.warning(
                "Failed to load code artifact for review context",
                extra={"artifact_id": artifact.get("id"), "conversation_id": conversation.get("id")},
            )
            continue

        numbered_content = code_artifacts.format_code_context(
            content,
            max_lines=config.CODE_ARTIFACT_CONTEXT_MAX_LINES,
            max_chars=config.CODE_ARTIFACT_CONTEXT_MAX_CHARS,
        )
        if not numbered_content:
            continue

        language = artifact.get("language") or "Text"
        summary = artifact.get("summary") or f"{artifact.get('line_count', 0)} lines"
        symbols = code_artifacts.extract_symbol_index(content)
        imports = code_artifacts.extract_import_paths(content)
        sections.append(
            "CODE REVIEW ARTIFACT:\n"
            f"- File: {artifact.get('label', artifact.get('filename', 'Artifact'))}\n"
            f"- Language: {language}\n"
            f"- Summary: {summary}\n"
            f"- Top-level symbols: {', '.join(symbol['name'] for symbol in symbols[:8]) or 'None'}\n"
            f"- Imports: {', '.join(imports[:8]) or 'None'}\n"
            "Use the numbered lines below when citing issues.\n"
            f"```text\n{numbered_content}\n```"
        )

    return merge_context_blocks(*sections)


@app.get("/api/health")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.post("/api/auth/login", response_model=LoginResponse, dependencies=[Depends(security.rate_limiter(requests_limit=5, time_window=60, scope="auth"))])
async def login(request: auth.GoogleLoginRequest):
    """
    Verify Google ID token and return session JWT.
    """
    # Verify Google token
    google_user = auth.verify_google_token(request.id_token)
    email = google_user.get("email")

    # Security: Validate user access against allowlists.
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided in token")
    auth.validate_user_access(email)

    # Create session token
    user_id = google_user["sub"]
    access_token = auth.create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": google_user.get("email"),
            "name": google_user.get("name"),
            "picture": google_user.get("picture")
        }
    }


@app.get("/api/auth/config", response_model=AuthConfigResponse)
async def get_auth_config():
    """Public auth config needed by the login UI."""
    return {"google_client_id": auth.GOOGLE_CLIENT_ID}


@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = "md",
    user_id: str = Depends(auth.get_current_user_id)
):
    """Export a conversation to Markdown or PDF."""
    conversation = await storage.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if format == "md":
        content = export.export_to_markdown(conversation)
        return StreamingResponse(
            io.StringIO(content),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=conversation_{conversation_id}.md"}
        )
    elif format == "pdf":
        content_bytes = export.export_to_pdf(conversation)
        return StreamingResponse(
            io.BytesIO(content_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=conversation_{conversation_id}.pdf"}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'md' or 'pdf'.")


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(user_id: str = Depends(auth.get_current_user_id)):
    """List conversations for the current user."""
    return await storage.list_conversations(user_id)


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(auth.get_current_user_id)):
    """Delete a conversation."""
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    artifact_paths = _get_file_backed_artifact_paths(conversation.get("primary_artifacts"))
    try:
        await storage.delete_conversation(conversation_id, user_id)
        for relative_path in artifact_paths:
            await run_in_threadpool(image_artifacts.delete_image_file, relative_path)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.error("Error deleting conversation", exc_info=False)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/models")
async def list_models(user_id: str = Depends(auth.get_current_user_id)):
    """Fetch available models from OpenRouter."""
    try:
        models = await openrouter.fetch_models()
        return models
    except Exception:
        logger.error("Error fetching models", exc_info=False)
        # Security: Do not leak internal error details to client
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/status")
async def get_status(user_id: str = Depends(auth.get_current_user_id)):
    """Get infrastructure status."""
    from . import config
    is_db = bool(config.DATABASE_URL)
    return {
        "storage_mode": "database" if is_db else "filesystem",
        "origin": config.APP_ORIGIN,
        "database_url_configured": is_db
    }


@app.post("/api/conversations", response_model=Conversation, dependencies=[Depends(security.rate_limiter(requests_limit=10, time_window=60, scope="create_conv"))])
async def create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(auth.get_current_user_id)
):
    """Create a new conversation for the current user."""
    conversation_id = str(uuid.uuid4())
    conversation = await storage.create_conversation(
        conversation_id, 
        user_id, 
        request.framework,
        request.council_models,
        request.chairman_model,
        session_type=request.session_type,
        specialist_template_id=request.specialist_template_id,
        execution_mode=request.execution_mode,
        primary_artifacts=[
            artifact.model_dump(exclude_none=True)
            for artifact in request.primary_artifacts
        ],
    )
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(auth.get_current_user_id)
):
    """Get a specific conversation if owned by current user."""
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/conversations/{conversation_id}/documents", response_model=List[DocumentMetadata])
async def list_documents(
    conversation_id: str,
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await storage.list_documents(conversation_id, user_id)


@app.post(
    "/api/conversations/{conversation_id}/documents",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(security.rate_limiter(requests_limit=10, time_window=60, scope="upload_docs"))]
)
async def upload_documents(
    conversation_id: str,
    files: List[UploadFile] = File(...),
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    existing_documents = await storage.list_documents(conversation_id, user_id)
    if len(existing_documents) + len(files) > config.PDF_MAX_FILES_PER_CONVERSATION:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {config.PDF_MAX_FILES_PER_CONVERSATION} PDFs per conversation."
        )

    uploaded_documents: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for upload in files:
        filename = upload.filename or "document.pdf"
        if not documents.is_pdf_file(filename, upload.content_type):
            errors.append({"filename": filename, "error": "Only PDF files are supported."})
            continue

        content = await upload.read(config.PDF_MAX_FILE_SIZE_BYTES + 1)
        if len(content) > config.PDF_MAX_FILE_SIZE_BYTES:
            errors.append({"filename": filename, "error": "File exceeds the 10MB limit."})
            continue
        if len(content) == 0:
            errors.append({"filename": filename, "error": "File is empty."})
            continue

        # Security: Validate PDF magic number
        if not documents.validate_pdf_header(content):
            errors.append({"filename": filename, "error": "Invalid file format. File does not appear to be a valid PDF."})
            continue

        doc = await storage.create_document(conversation_id, user_id, filename, len(content))
        try:
            # Offload CPU-bound PDF extraction to threadpool to avoid blocking event loop
            pages = await run_in_threadpool(documents.extract_pdf_text, content)
            if not any(page.strip() for page in pages):
                raise ValueError("No extractable text found in PDF.")

            chunks = documents.chunk_pages(pages)
            if not chunks:
                raise ValueError("No extractable text found in PDF.")

            # Offload heavy embedding model inference to threadpool
            embeddings = await run_in_threadpool(documents.embed_texts, [chunk["text"] for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise ValueError("Failed to embed document chunks.")

            chunk_records = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_records.append({
                    "document_id": doc["id"],
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "chunk_index": chunk["chunk_index"],
                    "page_number": chunk["page_number"],
                    "text": chunk["text"],
                    "embedding": embedding,
                })

            await storage.add_document_chunks(conversation_id, user_id, chunk_records)
            doc = await storage.update_document(
                conversation_id,
                doc["id"],
                user_id,
                status="ready",
                page_count=len(pages),
                error_message=None
            )
        except Exception as e:
            doc = await storage.update_document(
                conversation_id,
                doc["id"],
                user_id,
                status="failed",
                error_message=str(e)
            )
        artifact_record = build_primary_artifact_from_document(doc)
        if artifact_record:
            await storage.upsert_primary_artifact(conversation_id, user_id, artifact_record)
        uploaded_documents.append(doc)

    return {"documents": uploaded_documents, "errors": errors}


@app.delete("/api/conversations/{conversation_id}/documents/{document_id}")
async def delete_document(
    conversation_id: str,
    document_id: str,
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        await storage.delete_document(conversation_id, document_id, user_id)
        await storage.remove_primary_artifact_for_document(conversation_id, user_id, document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "success"}


@app.post(
    "/api/conversations/{conversation_id}/artifacts/images",
    response_model=ImageArtifactUploadResponse,
    dependencies=[Depends(security.rate_limiter(requests_limit=10, time_window=60, scope="upload_docs"))]
)
async def upload_image_artifacts(
    conversation_id: str,
    files: List[UploadFile] = File(...),
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if normalize_session_type(conversation.get("session_type")) != "visual_review":
        raise HTTPException(status_code=400, detail="Image uploads are only supported in Visual Review sessions.")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    existing_images = [
        artifact
        for artifact in normalize_primary_artifacts(conversation.get("primary_artifacts"))
        if artifact.get("kind") == "image"
    ]
    if len(existing_images) + len(files) > config.IMAGE_MAX_FILES_PER_CONVERSATION:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {config.IMAGE_MAX_FILES_PER_CONVERSATION} images per conversation.",
        )

    uploaded_artifacts: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for upload in files:
        filename = upload.filename or "image"
        if not image_artifacts.is_supported_image_file(filename, upload.content_type):
            errors.append({"filename": filename, "error": "Only PNG, JPEG, GIF, and WebP images are supported."})
            continue

        content = await upload.read(config.IMAGE_MAX_FILE_SIZE_BYTES + 1)
        if len(content) > config.IMAGE_MAX_FILE_SIZE_BYTES:
            errors.append({"filename": filename, "error": "File exceeds the 5MB limit."})
            continue
        if len(content) == 0:
            errors.append({"filename": filename, "error": "File is empty."})
            continue

        detected_type = image_artifacts.detect_image_type(content)
        if not detected_type:
            errors.append({"filename": filename, "error": "Unsupported or invalid image file."})
            continue

        _, mime_type, extension = detected_type
        artifact_id = str(uuid.uuid4())
        relative_path = await run_in_threadpool(
            image_artifacts.save_image_file,
            conversation_id,
            artifact_id,
            content,
            extension,
        )
        artifact_record = {
            "id": artifact_id,
            "kind": "image",
            "label": filename,
            "source": "upload",
            "status": "ready",
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "preview_url": image_artifacts.build_preview_url(relative_path),
            "storage_path": relative_path,
        }
        await storage.upsert_primary_artifact(conversation_id, user_id, artifact_record)
        uploaded_artifacts.append(artifact_record)

    return {"artifacts": uploaded_artifacts, "errors": errors}


@app.delete("/api/conversations/{conversation_id}/artifacts/images/{artifact_id}")
async def delete_image_artifact(
    conversation_id: str,
    artifact_id: str,
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    artifact = await storage.get_primary_artifact(conversation_id, user_id, artifact_id)
    if artifact is None or artifact.get("kind") != "image":
        raise HTTPException(status_code=404, detail="Image artifact not found")

    await run_in_threadpool(image_artifacts.delete_image_file, artifact.get("storage_path"))
    await storage.remove_primary_artifact_by_id(conversation_id, user_id, artifact_id)
    return {"status": "success"}


@app.post(
    "/api/conversations/{conversation_id}/artifacts/code-files",
    response_model=CodeArtifactUploadResponse,
    dependencies=[Depends(security.rate_limiter(requests_limit=10, time_window=60, scope="upload_docs"))]
)
async def upload_code_artifacts(
    conversation_id: str,
    files: List[UploadFile] = File(...),
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if normalize_session_type(conversation.get("session_type")) != "code_review":
        raise HTTPException(status_code=400, detail="Code file uploads are only supported in Code Review sessions.")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    existing_code_artifacts = [
        artifact
        for artifact in normalize_primary_artifacts(conversation.get("primary_artifacts"))
        if artifact.get("kind") == "code"
    ]
    if len(existing_code_artifacts) + len(files) > config.CODE_ARTIFACT_MAX_FILES_PER_CONVERSATION:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {config.CODE_ARTIFACT_MAX_FILES_PER_CONVERSATION} code artifacts per conversation.",
        )

    uploaded_artifacts: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for upload in files:
        filename = upload.filename or "artifact.txt"
        if not code_artifacts.is_supported_code_file(filename, upload.content_type):
            errors.append({"filename": filename, "error": "Only text-based code, diff, and config files are supported."})
            continue

        content_bytes = await upload.read(config.CODE_ARTIFACT_MAX_FILE_SIZE_BYTES + 1)
        if len(content_bytes) > config.CODE_ARTIFACT_MAX_FILE_SIZE_BYTES:
            errors.append({"filename": filename, "error": "File exceeds the 200KB limit."})
            continue
        if len(content_bytes) == 0:
            errors.append({"filename": filename, "error": "File is empty."})
            continue

        try:
            text_content = code_artifacts.decode_text_content(content_bytes)
        except ValueError as exc:
            errors.append({"filename": filename, "error": str(exc)})
            continue

        artifact_id = str(uuid.uuid4())
        storage_path = await run_in_threadpool(
            code_artifacts.save_code_file,
            conversation_id,
            artifact_id,
            filename,
            text_content,
        )
        line_count = code_artifacts.count_lines(text_content)
        language = code_artifacts.guess_language(filename)
        artifact_record = {
            "id": artifact_id,
            "kind": "code",
            "label": filename,
            "source": "upload",
            "status": "ready",
            "filename": filename,
            "mime_type": upload.content_type or "text/plain",
            "size_bytes": len(content_bytes),
            "storage_path": storage_path,
            "line_count": line_count,
            "language": language,
            "summary": code_artifacts.build_summary(filename, text_content),
        }
        await storage.upsert_primary_artifact(conversation_id, user_id, artifact_record)
        uploaded_artifacts.append(artifact_record)

    return {"artifacts": uploaded_artifacts, "errors": errors}


@app.delete("/api/conversations/{conversation_id}/artifacts/code/{artifact_id}")
async def delete_code_artifact(
    conversation_id: str,
    artifact_id: str,
    user_id: str = Depends(auth.get_current_user_id)
):
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    artifact = await storage.get_primary_artifact(conversation_id, user_id, artifact_id)
    if artifact is None or artifact.get("kind") != "code":
        raise HTTPException(status_code=404, detail="Code artifact not found")

    await run_in_threadpool(code_artifacts.delete_code_file, artifact.get("storage_path"))
    await storage.remove_primary_artifact_by_id(conversation_id, user_id, artifact_id)
    return {"status": "success"}


@app.post("/api/conversations/{conversation_id}/message", dependencies=[Depends(security.rate_limiter(requests_limit=20, time_window=60, scope="chat"))])
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(auth.get_current_user_id)
):
    """
    Send a message and run the 3-stage council process.
    """
    # Check if conversation exists and verify ownership
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    requested_council_models, effective_council_models, excluded_non_vision_models = (
        _resolve_stage1_models_for_conversation(conversation)
    )
    _visual_review_requires_vision_models(conversation, effective_council_models)

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    await storage.add_user_message(conversation_id, user_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        await storage.update_conversation_title(conversation_id, user_id, title)

    # Run the 3-stage council process
    framework = conversation.get("framework", "standard")
    chairman_model = conversation.get("chairman_model")

    history = _build_conversation_history(conversation, request.content)

    retrieval_context, citations = await retrieval.build_retrieval_context(
        conversation_id,
        user_id,
        request.content
    )
    effective_context = _build_effective_context(conversation, retrieval_context)
    effective_context = merge_context_blocks(
        effective_context,
        await _build_code_review_artifact_context(conversation),
    )

    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        history,
        framework=framework,
        council_models=effective_council_models,
        chairman_model=chairman_model,
        session_type=conversation.get("session_type"),
        specialist_template_id=conversation.get("specialist_template_id"),
        execution_mode=conversation.get("execution_mode"),
        primary_artifacts=conversation.get("primary_artifacts"),
        retrieval_context=effective_context,
        retrieval_citations=citations,
        conversation_messages=conversation.get("messages")
    )
    metadata["requested_council_models"] = requested_council_models
    metadata["effective_council_models"] = effective_council_models
    metadata["excluded_non_vision_models"] = excluded_non_vision_models
    metadata["session_type"] = conversation.get("session_type", DEFAULT_SESSION_TYPE)
    metadata["specialist_template_id"] = conversation.get("specialist_template_id")
    metadata["execution_mode"] = normalize_execution_mode(
        conversation.get("execution_mode"),
        session_type=conversation.get("session_type"),
    )
    metadata["specialist_template_label"] = get_template_label(
        conversation.get("specialist_template_id"),
        conversation.get("session_type"),
    )
    metadata["primary_artifacts"] = conversation.get("primary_artifacts", [])
    metadata["primary_artifact_count"] = len(conversation.get("primary_artifacts") or [])

    # Add assistant message with all stages
    await storage.add_assistant_message(
        conversation_id,
        user_id,
        stage1_results,
        stage2_results,
        stage3_result,
        metadata
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


def _extract_retry_model_name(model_label: Any) -> str:
    if not isinstance(model_label, str):
        return ""
    cleaned = model_label.strip()
    if cleaned.endswith(")") and " (" in cleaned:
        base, _ = cleaned.rsplit(" (", 1)
        return base.strip()
    return cleaned


def _is_retry_model_match(model_name: str, retry_model: str) -> bool:
    if model_name == retry_model:
        return True
    return model_name.startswith(f"{retry_model} (")


def _find_previous_user_message_index(messages: List[Dict[str, Any]], assistant_message_index: int) -> Optional[int]:
    for index in range(assistant_message_index - 1, -1, -1):
        if messages[index].get("role") == "user":
            return index
    return None


def _build_history_through_user_message(
    messages: List[Dict[str, Any]],
    user_message_index: int
) -> List[Dict[str, str]]:
    history: List[Dict[str, str]] = []
    for msg in messages[:user_message_index]:
        role = msg.get("role")
        if role == "user":
            history.append({"role": "user", "content": msg.get("content", "")})
            continue
        if role == "assistant":
            stage3 = msg.get("stage3")
            if isinstance(stage3, dict) and stage3.get("response"):
                history.append({"role": "assistant", "content": stage3["response"]})

    user_message = messages[user_message_index]
    history.append({"role": "user", "content": user_message.get("content", "")})
    return history


def _build_response_label_mapping(stage1_results: List[Dict[str, Any]]) -> Dict[str, str]:
    labels = [chr(65 + index) for index in range(len(stage1_results))]
    return {
        f"Response {label}": result["model"]
        for label, result in zip(labels, stage1_results)
    }


async def _rerun_stage2_and_stage3(
    *,
    framework: str,
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    effective_models: List[str],
    chairman_model: Optional[str],
    session_type: Optional[str],
    specialist_template_id: Optional[str],
    execution_mode: Optional[str],
    primary_artifacts: Optional[List[Dict[str, Any]]],
    retrieval_context: str,
    conversation_messages: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    stage2_results: List[Dict[str, Any]] = []
    aggregate_rankings: List[Dict[str, Any]] = []
    aggregate_rubrics: List[Dict[str, Any]] = []
    model_profiles = (
        build_model_weight_profile(conversation_messages, effective_models)
        if framework == "heterogeneous" else {}
    )

    if framework == "ensemble":
        label_to_model = _build_response_label_mapping(stage1_results)
    elif framework == "debate":
        stage2_results, label_to_model = await stage2_collect_critiques(
            user_query,
            stage1_results,
            effective_models,
            retrieval_context=retrieval_context
        )
    else:
        stage2_results, label_to_model = await stage2_collect_rankings(
            user_query,
            stage1_results,
            effective_models,
            chairman_model,
            retrieval_context=retrieval_context,
            session_type=session_type,
            framework=framework,
            model_profiles=model_profiles
        )
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        aggregate_rubrics = calculate_aggregate_rubrics(
            stage2_results,
            label_to_model,
            session_type=session_type,
        )

    updated_model_profiles = (
        apply_round_to_model_profiles(
            model_profiles,
            aggregate_rankings,
            [result["model"] for result in stage1_results]
        )
        if framework == "heterogeneous" and aggregate_rankings else model_profiles
    )

    execution_report = await run_code_execution_loop(
        session_type=session_type,
        execution_mode=execution_mode,
        user_query=user_query,
        stage1_results=stage1_results,
        stage2_results=stage2_results,
        chairman_model=chairman_model or config.CHAIRMAN_MODEL,
        primary_artifacts=primary_artifacts,
        retrieval_context=retrieval_context,
    )
    execution_context = build_execution_context_block(execution_report)

    full_stage3_response = ""
    async for token in stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        chairman_model=chairman_model,
        mode=framework,
        session_type=session_type,
        specialist_template_id=specialist_template_id,
        retrieval_context=retrieval_context,
        execution_context=execution_context,
        aggregate_rankings=aggregate_rankings,
        aggregate_rubrics=aggregate_rubrics,
    ):
        full_stage3_response += token

    if not full_stage3_response.strip():
        raise RuntimeError("The chairman model returned an empty response.")

    visual_findings: List[Dict[str, Any]] = []
    if session_type == "visual_review":
        full_stage3_response, visual_findings = extract_visual_findings_from_response(
            full_stage3_response,
            primary_artifacts=primary_artifacts,
        )

    stage3_result = {
        "model": chairman_model or config.CHAIRMAN_MODEL,
        "response": full_stage3_response
    }

    return {
        "stage2": stage2_results,
        "stage3": stage3_result,
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "aggregate_rubrics": aggregate_rubrics,
        "execution": execution_report,
        "visual_findings": visual_findings,
        "model_weight_profile": serialize_model_weight_profile(updated_model_profiles, effective_models)
        if framework == "heterogeneous" else [],
        "ballot_weighting": {
            "mode": "confidence_x_rolling_performance",
            "confidence_source": "stage2_self_report",
            "history_source": "prior_conversation_rankings",
        } if framework == "heterogeneous" else None,
    }


@app.post(
    "/api/conversations/{conversation_id}/messages/{message_index}/retry-stage1",
    dependencies=[Depends(security.rate_limiter(requests_limit=20, time_window=60, scope="chat"))]
)
async def retry_failed_stage1_models(
    conversation_id: str,
    message_index: int,
    request: RetryStage1Request,
    user_id: str = Depends(auth.get_current_user_id)
):
    """
    Retry Stage 1 only for models that failed on a prior assistant message.
    """
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = conversation.get("messages", [])
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(status_code=404, detail="Message not found")

    target_message = messages[message_index]
    if target_message.get("role") != "assistant":
        raise HTTPException(status_code=400, detail="Retry is only supported for assistant messages")

    existing_metadata = target_message.get("metadata")
    metadata: Dict[str, Any] = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
    existing_stage1 = target_message.get("stage1")
    stage1_results: List[Dict[str, Any]] = list(existing_stage1) if isinstance(existing_stage1, list) else []

    existing_stage1_errors = metadata.get("stage1_errors")
    normalized_existing_errors: List[Dict[str, str]] = []
    if isinstance(existing_stage1_errors, list):
        for error_item in existing_stage1_errors:
            if not isinstance(error_item, dict):
                continue
            model_label = error_item.get("model")
            error_text = error_item.get("error")
            if not isinstance(model_label, str):
                continue
            normalized_existing_errors.append({
                "model": model_label,
                "error": str(error_text) if error_text is not None else "Unknown error",
            })

    failed_models_from_message: List[str] = []
    failed_seen = set()
    for error_item in normalized_existing_errors:
        model_name = _extract_retry_model_name(error_item.get("model"))
        if not model_name or model_name in failed_seen:
            continue
        failed_seen.add(model_name)
        failed_models_from_message.append(model_name)

    requested_models = (
        []
        if request.refresh_synthesis and not request.models
        else (request.models if request.models else failed_models_from_message)
    )
    if not requested_models and not request.refresh_synthesis:
        raise HTTPException(status_code=400, detail="No failed models found to retry")

    deduped_requested_models: List[str] = []
    request_seen = set()
    for model_name in requested_models:
        normalized_name = _extract_retry_model_name(model_name)
        if not normalized_name or normalized_name in request_seen:
            continue
        request_seen.add(normalized_name)
        deduped_requested_models.append(normalized_name)

    _, configured_effective_models, excluded_non_vision_models = _resolve_stage1_models_for_conversation(conversation)
    _visual_review_requires_vision_models(conversation, configured_effective_models)

    effective_models = metadata.get("effective_council_models")
    if isinstance(effective_models, list) and effective_models:
        allowed_effective_models = set(configured_effective_models)
        effective_models = [model_name for model_name in effective_models if model_name in allowed_effective_models]
    else:
        effective_models = []
    if not effective_models:
        effective_models = configured_effective_models
    allowed_models = set(effective_models)

    retry_models = [model_name for model_name in deduped_requested_models if model_name in allowed_models]
    if deduped_requested_models and not retry_models:
        raise HTTPException(status_code=400, detail="No retriable models in request")

    history: List[Dict[str, str]] = []
    retry_query = ""
    retrieval_context = ""
    effective_context = ""
    citations: List[Dict[str, Any]] = []
    if retry_models or request.refresh_synthesis:
        previous_user_index = _find_previous_user_message_index(messages, message_index)
        if previous_user_index is None:
            raise HTTPException(status_code=400, detail="No matching user message found for retry")

        history = _build_history_through_user_message(messages, previous_user_index)
        retry_query = history[-1]["content"] if history else ""
        if not retry_query.strip():
            raise HTTPException(status_code=400, detail="Cannot retry an empty prompt")
        history[-1] = {
            "role": "user",
            "content": _build_user_message_content(conversation, retry_query),
        }

        retrieval_context, citations = await retrieval.build_retrieval_context(
            conversation_id,
            user_id,
            retry_query
        )
        effective_context = _build_effective_context(conversation, retrieval_context)
        effective_context = merge_context_blocks(
            effective_context,
            await _build_code_review_artifact_context(conversation),
        )

    retry_stage1_results: List[Dict[str, Any]] = []
    retry_stage1_errors: List[Dict[str, str]] = []
    if retry_models:
        async for result in stage1_collect_responses(
            history,
            retry_models,
            retrieval_context=effective_context
        ):
            if result.get("error"):
                retry_stage1_errors.append({
                    "model": result.get("model", "unknown"),
                    "error": result.get("error", "Unknown error")
                })
            else:
                retry_stage1_results.append(result)

    retry_model_set = set(retry_models)
    merged_stage1: List[Dict[str, Any]] = []
    for item in stage1_results:
        model_name = item.get("model")
        if not isinstance(model_name, str):
            continue
        if any(_is_retry_model_match(model_name, retry_model) for retry_model in retry_model_set):
            continue
        merged_stage1.append(item)
    merged_stage1.extend(retry_stage1_results)

    remaining_previous_errors: List[Dict[str, str]] = []
    for error_item in normalized_existing_errors:
        previous_model = _extract_retry_model_name(error_item.get("model"))
        if previous_model in retry_model_set:
            continue
        remaining_previous_errors.append(error_item)
    combined_errors = remaining_previous_errors + retry_stage1_errors

    responded_models: List[str] = []
    responded_seen = set()
    for item in merged_stage1:
        model_name = item.get("model")
        if isinstance(model_name, str) and model_name not in responded_seen:
            responded_seen.add(model_name)
            responded_models.append(model_name)

    retry_history = metadata.get("stage1_retry_history")
    retry_history = list(retry_history) if isinstance(retry_history, list) else []
    if retry_models:
        retry_history.append({
            "retried_models": retry_models,
            "recovered_models": [item["model"] for item in retry_stage1_results],
            "failed_models": [item["model"] for item in retry_stage1_errors],
            "timestamp_ms": int(time.time() * 1000),
        })

    metadata["stage1_errors"] = combined_errors
    metadata["responded_council_models"] = responded_models
    metadata["stage1_retry_history"] = retry_history
    metadata["retrieval"] = {"citations": citations}
    metadata["session_type"] = conversation.get("session_type", DEFAULT_SESSION_TYPE)
    metadata["specialist_template_id"] = conversation.get("specialist_template_id")
    metadata["execution_mode"] = normalize_execution_mode(
        conversation.get("execution_mode"),
        session_type=conversation.get("session_type"),
    )
    metadata["specialist_template_label"] = get_template_label(
        conversation.get("specialist_template_id"),
        conversation.get("session_type"),
    )
    metadata["primary_artifacts"] = conversation.get("primary_artifacts", [])
    metadata["primary_artifact_count"] = len(conversation.get("primary_artifacts") or [])
    metadata["excluded_non_vision_models"] = excluded_non_vision_models

    if conversation.get("framework") == "six_hats":
        metadata["retry_note"] = "Retry runs use direct model calls and do not re-assign Six Hats roles."

    target_message["stage1"] = merged_stage1
    target_message["metadata"] = metadata

    synthesis_refreshed = False
    synthesis_refresh_error: Optional[str] = None
    if request.refresh_synthesis:
        if not merged_stage1:
            synthesis_refresh_error = "Cannot refresh synthesis without Stage 1 responses."
        else:
            active_chairman_model = metadata.get("chairman_model")
            if not isinstance(active_chairman_model, str) or not active_chairman_model:
                active_chairman_model = conversation.get("chairman_model") or config.CHAIRMAN_MODEL
            framework = conversation.get("framework", "standard")

            refresh_started_at = time.monotonic()
            try:
                refreshed_data = await _rerun_stage2_and_stage3(
                    framework=framework,
                    user_query=retry_query,
                    stage1_results=merged_stage1,
                    effective_models=effective_models,
                    chairman_model=active_chairman_model,
                    session_type=conversation.get("session_type"),
                    specialist_template_id=conversation.get("specialist_template_id"),
                    execution_mode=conversation.get("execution_mode"),
                    primary_artifacts=conversation.get("primary_artifacts"),
                    retrieval_context=effective_context,
                    conversation_messages=messages[:message_index]
                )
                target_message["stage2"] = refreshed_data["stage2"]
                target_message["stage3"] = refreshed_data["stage3"]
                metadata["label_to_model"] = refreshed_data["label_to_model"]
                metadata["aggregate_rankings"] = refreshed_data["aggregate_rankings"]
                metadata["aggregate_rubrics"] = refreshed_data["aggregate_rubrics"]
                metadata["execution"] = refreshed_data["execution"]
                metadata["visual_findings"] = refreshed_data["visual_findings"]
                if refreshed_data.get("model_weight_profile"):
                    metadata["model_weight_profile"] = refreshed_data["model_weight_profile"]
                if refreshed_data.get("ballot_weighting"):
                    metadata["ballot_weighting"] = refreshed_data["ballot_weighting"]
                metadata["synthesis_refreshed_at_ms"] = int(time.time() * 1000)
                metadata["synthesis_refresh_duration_seconds"] = round(time.monotonic() - refresh_started_at, 3)
                metadata.pop("synthesis_refresh_error", None)
                synthesis_refreshed = True
            except Exception:
                synthesis_refresh_error = "Failed to refresh synthesis."
                metadata["synthesis_refresh_error"] = synthesis_refresh_error

    await storage.update_message(conversation_id, user_id, message_index, target_message)

    return {
        "stage1": merged_stage1,
        "stage2": target_message.get("stage2"),
        "stage3": target_message.get("stage3"),
        "stage1_errors": combined_errors,
        "retried_models": retry_models,
        "recovered_models": [item["model"] for item in retry_stage1_results],
        "failed_models": [item["model"] for item in retry_stage1_errors],
        "synthesis_refreshed": synthesis_refreshed,
        "synthesis_refresh_error": synthesis_refresh_error,
        "metadata": metadata,
    }


@app.post("/api/conversations/{conversation_id}/message/stream", dependencies=[Depends(security.rate_limiter(requests_limit=20, time_window=60, scope="chat"))])
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(auth.get_current_user_id)
):
    """
    Send a message and stream the 3-stage council process.
    """
    # Check if conversation exists and verify ownership
    conversation = await storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0
    framework = conversation.get("framework", "standard")
    chairman_model = conversation.get("chairman_model")
    requested_council_models, effective_council_models, excluded_non_vision_models = (
        _resolve_stage1_models_for_conversation(conversation)
    )
    _visual_review_requires_vision_models(conversation, effective_council_models)
    model_profiles = (
        build_model_weight_profile(conversation.get("messages"), effective_council_models)
        if framework == "heterogeneous" else {}
    )

    async def event_generator():
        overall_start = time.monotonic()
        try:
            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            history = _build_conversation_history(conversation, request.content)

            # ⚡ Bolt: Run storage (I/O) and retrieval (CPU/Network) in parallel
            # We use gather to ensure both complete before proceeding, propagating exceptions.
            # add_user_message returns None, build_retrieval_context returns tuple.
            _, (retrieval_context, citations) = await asyncio.gather(
                storage.add_user_message(conversation_id, user_id, request.content),
                retrieval.build_retrieval_context(conversation_id, user_id, request.content)
            )
            effective_context = _build_effective_context(conversation, retrieval_context)
            effective_context = merge_context_blocks(
                effective_context,
                await _build_code_review_artifact_context(conversation),
            )

            logger.info(
                f"[stream] conversation={conversation_id} framework={framework} "
                f"requested_models={requested_council_models} effective_models={effective_council_models} "
                f"chairman={chairman_model or config.CHAIRMAN_MODEL}"
            )

            # Stage 1: Collect responses (incremental)
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_start = time.monotonic()
            stage1_results = []
            stage1_errors = []

            if framework == "six_hats":
                stage1_results, stage1_errors = await stage1_collect_responses_six_hats(
                    history,
                    effective_council_models,
                    retrieval_context=effective_context
                )
                for error in stage1_errors:
                    yield f"data: {json.dumps({'type': 'stage1_error', 'data': error})}\n\n"
            else:
                async for result in stage1_collect_responses(history, effective_council_models, retrieval_context=effective_context):
                    if result.get("error"):
                        stage1_errors.append(result)
                        yield f"data: {json.dumps({'type': 'stage1_error', 'data': result})}\n\n"
                    else:
                        stage1_results.append(result)
                        yield f"data: {json.dumps({'type': 'stage1_update', 'data': result})}\n\n"

            stage1_duration = round(time.monotonic() - stage1_start, 3)
            responded_council_models = [result["model"] for result in stage1_results]
            stage1_meta = {
                "requested_council_models": requested_council_models,
                "effective_council_models": effective_council_models,
                "excluded_non_vision_models": excluded_non_vision_models,
                "responded_council_models": responded_council_models,
                "stage1_errors": stage1_errors,
                "stage1_duration_seconds": stage1_duration,
            }
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results, 'metadata': stage1_meta})}\n\n"
            logger.info(
                f"[stream] conversation={conversation_id} stage1_complete duration={stage1_duration}s "
                f"responded={responded_council_models} errors={len(stage1_errors)}"
            )

            if not stage1_results:
                yield f"data: {json.dumps({'type': 'error', 'error': 'All selected models failed to respond. Please check your OpenRouter permissions or model availability.'})}\n\n"
                return

            # Stage 2: Collect rankings/critiques (Batch for now)
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_start = time.monotonic()
            stage2_results = []
            aggregate_rankings = []
            aggregate_rubrics = []
            label_to_model = {}
            updated_model_profiles = model_profiles
            retrieval_meta = {"retrieval": {"citations": citations}}
            config_meta = {
                "requested_council_models": requested_council_models,
                "effective_council_models": effective_council_models,
                "excluded_non_vision_models": excluded_non_vision_models,
                "responded_council_models": responded_council_models,
                "stage1_errors": stage1_errors,
            }
            hetero_meta = {}

            if framework == "ensemble":
                label_to_model = {f"Response {chr(65+i)}": r['model'] for i, r in enumerate(stage1_results)}
                yield f"data: {json.dumps({'type': 'stage2_skipped', 'metadata': {'label_to_model': label_to_model, **config_meta, **retrieval_meta}})}\n\n"
            
            elif framework == "debate":
                 stage2_results, label_to_model = await stage2_collect_critiques(
                     request.content,
                     stage1_results,
                     effective_council_models,
                     retrieval_context=effective_context
                 )
                 yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'mode': 'debate', **config_meta, **retrieval_meta}})}\n\n"

            else: # standard, six_hats, and heterogeneous all use ranking for Stage 2
                 stage2_results, label_to_model = await stage2_collect_rankings(
                     request.content,
                     stage1_results,
                     effective_council_models,
                     chairman_model,
                     retrieval_context=effective_context,
                     session_type=conversation.get("session_type"),
                     framework=framework,
                     model_profiles=model_profiles
                 )
                 aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
                 aggregate_rubrics = calculate_aggregate_rubrics(
                     stage2_results,
                     label_to_model,
                     session_type=conversation.get("session_type"),
                 )
                 if framework == "heterogeneous":
                     updated_model_profiles = apply_round_to_model_profiles(
                         model_profiles,
                         aggregate_rankings,
                         responded_council_models
                     )
                     hetero_meta = {
                         "model_weight_profile": serialize_model_weight_profile(
                             updated_model_profiles,
                             effective_council_models
                         ),
                         "ballot_weighting": {
                             "mode": "confidence_x_rolling_performance",
                             "confidence_source": "stage2_self_report",
                             "history_source": "prior_conversation_rankings",
                         },
                     }
                 yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings, 'aggregate_rubrics': aggregate_rubrics, **hetero_meta, **config_meta, **retrieval_meta}})}\n\n"

            stage2_duration = round(time.monotonic() - stage2_start, 3)
            logger.info(
                f"[stream] conversation={conversation_id} stage2_complete duration={stage2_duration}s "
                f"framework={framework}"
            )

            execution_report = await _run_code_execution_for_conversation(
                conversation,
                user_query=request.content,
                stage1_results=stage1_results,
                stage2_results=stage2_results,
                retrieval_context=effective_context,
                chairman_model=chairman_model or config.CHAIRMAN_MODEL,
            )
            execution_context = build_execution_context_block(execution_report)

            # Stage 3: Synthesize final answer (Streaming)
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_start = time.monotonic()
            full_stage3_response = ""
            async for token in stage3_synthesize_final(
                request.content,
                stage1_results,
                stage2_results,
                chairman_model=chairman_model,
                mode=framework,
                session_type=conversation.get("session_type"),
                specialist_template_id=conversation.get("specialist_template_id"),
                retrieval_context=effective_context,
                execution_context=execution_context,
                aggregate_rankings=aggregate_rankings,
                aggregate_rubrics=aggregate_rubrics,
            ):
                full_stage3_response += token
                yield f"data: {json.dumps({'type': 'stage3_token', 'data': token})}\n\n"

            if not full_stage3_response.strip():
                raise RuntimeError("The chairman model returned an empty response.")

            visual_findings: List[Dict[str, Any]] = []
            if conversation.get("session_type") == "visual_review":
                full_stage3_response, visual_findings = extract_visual_findings_from_response(
                    full_stage3_response,
                    primary_artifacts=conversation.get("primary_artifacts"),
                )
            
            stage3_result = {
                "model": chairman_model or config.CHAIRMAN_MODEL,
                "response": full_stage3_response
            }
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"
            stage3_duration = round(time.monotonic() - stage3_start, 3)
            logger.info(f"[stream] conversation={conversation_id} stage3_complete duration={stage3_duration}s")

            # Wait for title generation if it was started
            if title_task:
                 title = await title_task
                 await storage.update_conversation_title(conversation_id, user_id, title)
                 yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            metadata = {
                "framework": framework,
                "requested_council_models": requested_council_models,
                "effective_council_models": effective_council_models,
                "excluded_non_vision_models": excluded_non_vision_models,
                "responded_council_models": responded_council_models,
                "council_models": [r['model'] for r in stage1_results],
                "chairman_model": chairman_model or config.CHAIRMAN_MODEL,
                "label_to_model": label_to_model,
                "aggregate_rankings": aggregate_rankings,
                "aggregate_rubrics": aggregate_rubrics,
                "execution": execution_report,
                "visual_findings": visual_findings,
                "stage1_errors": stage1_errors,
                "session_type": conversation.get("session_type", DEFAULT_SESSION_TYPE),
                "specialist_template_id": conversation.get("specialist_template_id"),
                "execution_mode": normalize_execution_mode(
                    conversation.get("execution_mode"),
                    session_type=conversation.get("session_type"),
                ),
                "specialist_template_label": get_template_label(
                    conversation.get("specialist_template_id"),
                    conversation.get("session_type"),
                ),
                "primary_artifacts": conversation.get("primary_artifacts", []),
                "primary_artifact_count": len(conversation.get("primary_artifacts") or []),
                "timing": {
                    "stage1_seconds": stage1_duration,
                    "stage2_seconds": stage2_duration,
                    "stage3_seconds": stage3_duration,
                    "total_seconds": round(time.monotonic() - overall_start, 3),
                },
                **retrieval_meta
            }
            if framework == "heterogeneous":
                metadata["model_weight_profile"] = serialize_model_weight_profile(
                    updated_model_profiles,
                    effective_council_models
                )
                metadata["ballot_weighting"] = {
                    "mode": "confidence_x_rolling_performance",
                    "confidence_source": "stage2_self_report",
                    "history_source": "prior_conversation_rankings",
                }
            await storage.add_assistant_message(
                conversation_id,
                user_id,
                stage1_results,
                stage2_results,
                stage3_result,
                metadata
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            logger.info(
                f"[stream] conversation={conversation_id} complete total={metadata['timing']['total_seconds']}s "
                f"requested={requested_council_models} effective={effective_council_models} "
                f"responded={responded_council_models}"
            )

        except Exception:
            logger.error("Streaming error", exc_info=False)
            # Security: Do not leak internal error details to client
            yield f"data: {json.dumps({'type': 'error', 'error': 'An internal error occurred.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )



# ... existing code ...

# Serve frontend in production (if dist exists)
# This usually runs inside Docker where frontend is built to /app/frontend/dist
# or relative to working directory.
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API routes to pass through (though they should be matched above)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Return index.html for all other routes (SPA routing)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
