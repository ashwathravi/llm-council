"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio
import os
import requests
from contextlib import asynccontextmanager

from . import storage, auth, openrouter
from .database import init_db
from .council import (
    run_full_council, generate_conversation_title,
    stage1_collect_responses, stage1_collect_responses_six_hats,
    stage2_collect_rankings, stage2_collect_critiques,
    stage3_synthesize_final, calculate_aggregate_rankings
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (create tables) on startup
    await init_db()
    yield

app = FastAPI(title="LLM Council API", lifespan=lifespan)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    framework: str = "standard"
    council_models: List[str] = []
    chairman_model: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    framework: str = "standard"
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    framework: str = "standard"
    council_models: List[str] | None = None
    chairman_model: str | None = None
    messages: List[Dict[str, Any]]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


@app.get("/api/health")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: auth.GoogleLoginRequest):
    """
    Verify Google ID token and return session JWT.
    """
    # Verify Google token
    google_user = auth.verify_google_token(request.id_token)
    
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



@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(user_id: str = Depends(auth.get_current_user_id)):
    """List conversations for the current user."""
    return await storage.list_conversations(user_id)


@app.get("/api/models")
async def list_models(user_id: str = Depends(auth.get_current_user_id)):
    """Fetch available models from OpenRouter."""
    try:
        models = await openrouter.fetch_models()
        return models
    except Exception as e:
        print(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")

@app.get("/api/status")
async def get_status():
    """Get infrastructure status."""
    from . import config
    is_db = bool(config.DATABASE_URL)
    return {
        "storage_mode": "database" if is_db else "filesystem",
        "origin": config.APP_ORIGIN,
        "database_url_configured": is_db
    }


@app.post("/api/conversations", response_model=Conversation)
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
        request.chairman_model
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


@app.post("/api/conversations/{conversation_id}/message")
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
    council_models = conversation.get("council_models", [])
    chairman_model = conversation.get("chairman_model")

    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        framework=framework,
        council_models=council_models,
        chairman_model=chairman_model
    )

    # Add assistant message with all stages
    await storage.add_assistant_message(
        conversation_id,
        user_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
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
    council_models = conversation.get("council_models", [])
    chairman_model = conversation.get("chairman_model")

    async def event_generator():
        try:

            # Add user message
            await storage.add_user_message(conversation_id, user_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            
            if framework == "six_hats":
                stage1_results = await stage1_collect_responses_six_hats(request.content, council_models)
            else:
                stage1_results = await stage1_collect_responses(request.content, council_models)
                
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings/critiques
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            
            if framework == "ensemble":
                # Ensemble: Skip Stage 2
                stage2_results = []
                label_to_model = {f"Response {chr(65+i)}": r['model'] for i, r in enumerate(stage1_results)}
                aggregate_rankings = []
                yield f"data: {json.dumps({'type': 'stage2_skipped', 'metadata': {'label_to_model': label_to_model}})}\n\n"
            
            elif framework == "debate":
                 # Debate: Stage 2 is Critiques
                 stage2_results, label_to_model = await stage2_collect_critiques(request.content, stage1_results, council_models)
                 yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'mode': 'debate'}})}\n\n"

            else: # standard and six_hats both use ranking for Stage 2
                 stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results, council_models, chairman_model)
                 aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
                 yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results, chairman_model=chairman_model, mode=framework)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
             if title_task:
                 title = await title_task
                 await storage.update_conversation_title(conversation_id, user_id, title)
                 yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            await storage.add_assistant_message(
                conversation_id,
                user_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

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
        uvicorn.run(app, host="0.0.0.0", port=8001)
else:
    # Development mode or no build found
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
