
import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL

DEFAULT_REFERER = "https://llm-council.local"
logger = logging.getLogger(__name__)

# Global shared client
_client: Optional[httpx.AsyncClient] = None

async def init_client():
    """Initialize the shared httpx client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient()

async def close_client():
    """Close the shared httpx client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None

async def get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client

def _get_request_id(response: httpx.Response) -> Optional[str]:
    return (
        response.headers.get("x-request-id")
        or response.headers.get("x-openrouter-request-id")
        or response.headers.get("openai-request-id")
    )

def _get_provider(response: httpx.Response) -> Optional[str]:
    return response.headers.get("x-openrouter-provider")

def _normalize_message_content(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, dict):
                    text = text.get("value") or text.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        content = "\n".join(parts)
    elif content is None:
        content = ""
    elif not isinstance(content, str):
        content = str(content)
    return content.strip()


def _extract_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or "Unknown error"

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("error") or str(error)
        if isinstance(error, str):
            return error
        if "message" in data:
            return str(data["message"])

    return response.text or "Unknown error"

async def fetch_models() -> List[Dict[str, Any]]:
    """
    Fetch available models from OpenRouter.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": DEFAULT_REFERER,
        }

        client = await get_client()
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json().get("data", [])

        # Filter logic
        models = []
        for m in data:
            # Basic filter for now, or match previous logic
            supported_params = m.get("supported_parameters", [])
            if "tools" in supported_params: # Match previous logic
                models.append({
                    "id": m["id"],
                    "name": m["name"],
                    "description": m.get("description", ""),
                    "context_length": m.get("context_length", 0),
                    "pricing": m.get("pricing", {}),
                    "architecture": m.get("architecture", {})
                })

        models.sort(key=lambda x: x["name"])
        return models
            
    except httpx.HTTPStatusError as e:
        message = _extract_error_message(e.response)
        raise RuntimeError(
            f"OpenRouter error {e.response.status_code}: {message}"
        ) from e
    except Exception as e:
        print(f"Error fetching models: {e}")
        raise e

async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    if not OPENROUTER_API_KEY:
        return {
            "content": None,
            "reasoning_details": None,
            "error": "OPENROUTER_API_KEY is not configured.",
            "status_code": None,
        }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": DEFAULT_REFERER,
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        client = await get_client()
        # Pass timeout to the request method, not client init
        response = await client.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()

        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            error_message = _extract_error_message(response)
            logger.error(
                "OpenRouter error payload: model=%s status=%s request_id=%s provider=%s error=%s",
                model,
                response.status_code,
                _get_request_id(response),
                _get_provider(response),
                error_message
            )
            return {
                "content": None,
                "reasoning_details": None,
                "error": error_message,
                "status_code": response.status_code,
            }

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            logger.error(
                "OpenRouter missing choices: model=%s status=%s request_id=%s provider=%s keys=%s",
                model,
                response.status_code,
                _get_request_id(response),
                _get_provider(response),
                list(data.keys()) if isinstance(data, dict) else type(data).__name__,
            )
            return {
                "content": None,
                "reasoning_details": None,
                "error": "Model returned no choices.",
                "status_code": response.status_code,
            }

        choice = choices[0]
        message = choice.get("message", {})

        content = _normalize_message_content(message)
        if not content:
            logger.warning(
                "OpenRouter returned empty content: model=%s status=%s request_id=%s provider=%s finish_reason=%s content_type=%s message_keys=%s usage=%s",
                model,
                response.status_code,
                _get_request_id(response),
                _get_provider(response),
                choice.get("finish_reason"),
                type(message.get("content")).__name__,
                list(message.keys()),
                data.get("usage") if isinstance(data, dict) else None
            )
            return {
                "content": None,
                "reasoning_details": message.get("reasoning_details"),
                "error": "Model returned an empty response.",
                "status_code": response.status_code,
            }

        return {
            "content": content,
            "reasoning_details": message.get("reasoning_details"),
            "error": None,
            "status_code": None,
        }

    except httpx.HTTPStatusError as e:
        message = _extract_error_message(e.response)
        error_message = f"{e.response.status_code}: {message}"
        logger.error("Error querying model %s: %s", model, error_message)
        return {
            "content": None,
            "reasoning_details": None,
            "error": error_message,
            "status_code": e.response.status_code,
        }
    except Exception as e:
        logger.exception("Error querying model %s", model)
        return {
            "content": None,
            "reasoning_details": None,
            "error": str(e),
            "status_code": None,
        }


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        timeout: Per-model timeout in seconds

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages, timeout=timeout) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}


async def query_model_stream(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
):
    """
    Query a single model with streaming.
    Yields content chunks (strings).
    """
    if not OPENROUTER_API_KEY:
        logger.error("Error querying model stream: OPENROUTER_API_KEY is not configured.")
        return

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": DEFAULT_REFERER, # Recommended by OpenRouter
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }

    try:
        client = await get_client()
        async with client.stream(
            "POST",
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        ) as response:
            response.raise_for_status()

            saw_done = False
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:].strip()
                if not data_str:
                    continue
                if data_str == "[DONE]":
                    saw_done = True
                    break

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    logger.warning("Malformed OpenRouter stream event for %s: %s", model, data_str[:200])
                    continue

                stream_error = data.get("error") if isinstance(data, dict) else None
                if stream_error:
                    if isinstance(stream_error, dict):
                        message = stream_error.get("message") or str(stream_error)
                    else:
                        message = str(stream_error)
                    raise RuntimeError(f"OpenRouter stream error for {model}: {message}")

                choices = data.get("choices") if isinstance(data, dict) else None
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                if not isinstance(delta, dict):
                    continue

                content = delta.get("content")
                if content:
                    yield content

            if not saw_done:
                logger.warning("OpenRouter stream for %s closed without [DONE] marker.", model)

    except Exception as e:
        logger.exception("Error querying model stream %s", model)
        raise RuntimeError(f"Streaming failed for model {model}: {e}") from e
