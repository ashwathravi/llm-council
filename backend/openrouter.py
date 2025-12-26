
import httpx
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL

DEFAULT_REFERER = "https://llm-council.local"


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
        async with httpx.AsyncClient() as client:
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
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                "content": message.get("content"),
                "reasoning_details": message.get("reasoning_details"),
                "error": None,
                "status_code": None,
            }

    except httpx.HTTPStatusError as e:
        message = _extract_error_message(e.response)
        error_message = f"{e.response.status_code}: {message}"
        print(f"Error querying model {model}: {error_message}")
        return {
            "content": None,
            "reasoning_details": None,
            "error": error_message,
            "status_code": e.response.status_code,
        }
    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return {
            "content": None,
            "reasoning_details": None,
            "error": str(e),
            "status_code": None,
        }


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

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
        print("Error querying model stream: OPENROUTER_API_KEY is not configured.")
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
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data['choices'][0]['delta']
                            content = delta.get('content')
                            if content:
                                yield content
                        except Exception:
                            continue
                            
    except Exception as e:
        print(f"Error querying model stream {model}: {e}")
        # Yield error message as content so UI sees something went wrong, 
        # or handle differently? unique error chunk?
        # For now, let's just log it. The generator will stop.
        pass
