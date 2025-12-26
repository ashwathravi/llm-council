"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model, query_model_stream
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL


async def stage1_collect_responses(messages: List[Dict[str, str]], council_models: List[str] = None):
    """
    Stage 1: Collect individual responses from all council models.
    Yields dicts with 'model' and 'response' keys as they complete.
    """
    active_models = council_models if council_models and len(council_models) > 0 else COUNCIL_MODELS
    import asyncio

    # Wrapper to attach model name to the task result
    async def query_with_name(model_name, msgs):
        response = await query_model(model_name, msgs)
        return model_name, response

    # Create tasks
    tasks = [query_with_name(model, messages) for model in active_models]

    # Yield results as they complete
    for completed_task in asyncio.as_completed(tasks):
        model, response = await completed_task
        if response and response.get("error"):
            yield {
                "model": model,
                "error": response.get("error")
            }
        elif response:
            yield {
                "model": model,
                "response": response.get('content', '')
            }


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: List[str] = None,
    chairman_model: str = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        council_models: Optional list of models to use. Defaults to config COUNCIL_MODELS.
        chairman_model: Unused here but kept for consistency if needed later.

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    active_models = council_models if council_models and len(council_models) > 0 else COUNCIL_MODELS
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(active_models, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None and not response.get("error"):
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use xiaomi/mimo-v2-flash:free for title generation
    response = await query_model("xiaomi/mimo-v2-flash:free", messages, timeout=30.0)

    if response is None or response.get("error"):
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(messages: List[Dict[str, str]], framework: str = "standard", council_models: list = None, chairman_model: str = None):
    """
    Orchestrates the selected council process.
    """
    # Extract latest user query for Stage 2/3 context
    # Assuming the last message is from the user
    latest_query = messages[-1]['content'] if messages and messages[-1]['role'] == 'user' else "Unknown Query"

    # Use provided models or fallback to config defaults
    active_council_models = council_models if council_models and len(council_models) > 0 else COUNCIL_MODELS
    active_chairman_model = chairman_model if chairman_model else CHAIRMAN_MODEL

    # Stage 1: Collect responses
    # We need to pass the full messages to stage 1 functions
    stage1_errors = []
    if framework == "six_hats":
        stage1_results, stage1_errors = await stage1_collect_responses_six_hats(messages, active_council_models)
    else:
        stage1_results = []
        async for result in stage1_collect_responses(messages, active_council_models):
            if result.get("error"):
                stage1_errors.append(result)
            else:
                stage1_results.append(result)

    if not stage1_results:
        stage3_result = {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }
        return [], [], stage3_result, {"stage1_errors": stage1_errors}

    # Stage 2: Rank or Critique
    if framework == "debate":
        stage2_results, label_to_model = await stage2_collect_critiques(latest_query, stage1_results, active_council_models)
    elif framework == "ensemble":
         # Ensemble doesn't use Stage 2 for logic, but we need to return something
         stage2_results = []
         # Create label mapping for synthesis even if no ranking
         labels = [chr(65 + i) for i in range(len(stage1_results))]
         label_to_model = {
             f"Response {label}": result['model']
             for label, result in zip(labels, stage1_results)
         }
    else:
        # Standard and Six Hats use ranking
        stage2_results, label_to_model = await stage2_collect_rankings(latest_query, stage1_results, active_council_models, active_chairman_model)

    # Calculate aggregate rankings if applicable
    aggregate_rankings = []
    if framework in ["standard", "six_hats"] and stage2_results:
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize
    stage3_result = await stage3_synthesize_final(
        latest_query, 
        stage1_results, 
        stage2_results, 
        active_chairman_model, # Pass chairman model
        mode=framework
    )

    metadata = {
        "framework": framework,
        "council_models": [r['model'] for r in stage1_results], # Actual models that responded
        "chairman_model": active_chairman_model,
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "stage1_errors": stage1_errors,
    }

    return stage1_results, stage2_results, stage3_result, metadata


# The following functions (run_standard_council, run_debate_council, etc.) are now
# superseded by the new run_full_council logic and can be removed or refactored
# if they are no longer called directly. For this change, we will keep them
# as they are not explicitly removed by the instruction, but note their redundancy.

async def run_standard_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """Standard 3-stage process."""
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)
    
    if not stage1_results:
        return _return_error()

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata


async def run_debate_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """Chain of Debate: Models critique each other."""
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)
    
    if not stage1_results:
        return _return_error()

    # Stage 2: Collect Critiques (instead of rankings)
    stage2_results, label_to_model = await stage2_collect_critiques(user_query, stage1_results)

    # Stage 3: Synthesize with critiques
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        mode="debate"
    )

    metadata = {
        "label_to_model": label_to_model,
        "mode": "debate"
    }
    
    return stage1_results, stage2_results, stage3_result, metadata


async def run_six_hats_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """Six Thinking Hats: Assigned perspectives."""
    # Stage 1: Collect responses with Hats
    stage1_results, _ = await stage1_collect_responses_six_hats(user_query)
    
    if not stage1_results:
        return _return_error()

    # Stage 2: Standard ranking (evaluates which perspective is most valuable)
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)
    
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        mode="six_hats"
    )

    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "mode": "six_hats"
    }

    return stage1_results, stage2_results, stage3_result, metadata


async def run_ensemble_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """Ensemble: Parallel query + unbiased synthesis (skip Stage 2)."""
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)
    
    if not stage1_results:
        return _return_error()

    # Stage 2: Skipped
    stage2_results = []
    
    # Create label mapping for synthesis
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Stage 3: Synthesize directly
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        mode="ensemble"
    )

    metadata = {
        "label_to_model": label_to_model,
        "mode": "ensemble"
    }

    return stage1_results, stage2_results, stage3_result, metadata


def _return_error():
    return [], [], {
        "model": "error",
        "response": "All models failed to respond. Please try again."
    }, {}


async def stage1_collect_responses_six_hats(
    messages: List[Dict[str, str]],
    council_models: List[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Stage 1 for Six Hats: Assign prompts to models."""
    active_models = council_models if council_models and len(council_models) > 0 else COUNCIL_MODELS
    hats = [
        ("White Hat", "Focus on available data and facts. Be neutral and objective."),
        ("Red Hat", "Focus on intuition, feelings, and hunches. No need to justify them."),
        ("Black Hat", "Focus on caution, risks, and potential problems. Be critical."),
        ("Yellow Hat", "Focus on benefits, optimism, and value. Be positive."),
        ("Green Hat", "Focus on creativity, alternatives, and new ideas."),
        ("Blue Hat", "Focus on process control, organization, and next steps.")
    ]
    
    # Assign hats to available models
    # If more models than hats, repeat/cycle hats. If fewer, some hats are missed.
    model_tasks = []
    assigned_hats = []
    
    for i, model in enumerate(active_models):
        hat_name, hat_prompt = hats[i % len(hats)]
        
        system_prompt = f"You are wearing the {hat_name}. {hat_prompt}"
        
        # Prepend system prompt to the FULL history
        current_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # We need to query models individually since they have different prompts
        # But we can still run them in parallel if we restructure query_models_parallel
        # For now, let's use a gathered list of coroutines
        model_tasks.append(query_model(model, current_messages))
        assigned_hats.append(hat_name)

    import asyncio
    responses = await asyncio.gather(*model_tasks)
    
    results = []
    errors = []
    for i, response in enumerate(responses):
        if response:
            model = active_models[i]
            hat = assigned_hats[i]
            model_label = f"{model} ({hat})"
            if response.get("error"):
                errors.append({
                    "model": model_label,
                    "error": response.get("error")
                })
            else:
                results.append({
                    "model": model_label,
                    "response": response.get('content', '')
                })

    return results, errors


async def stage2_collect_critiques(user_query: str, stage1_results: List[Dict[str, Any]], council_models: List[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Stage 2 for Debate: Critiques instead of rankings."""
    active_models = council_models if council_models and len(council_models) > 0 else COUNCIL_MODELS
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {f"Response {label}": result['model'] for label, result in zip(labels, stage1_results)}

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    critique_prompt = f"""You are participating in a debate about: "{user_query}"

Here are the arguments from other participants (anonymized):

{responses_text}

Your task:
1. Critically analyze each response. identifying weak points, logical fallacies, or missing information.
2. Highlight the strongest counter-arguments.
3. Be direct and constructive.

Provide your critique for each response."""

    messages = [{"role": "user", "content": critique_prompt}]
    
    responses = await query_models_parallel(active_models, messages)
    
    results = []
    for model, response in responses.items():
        if response and not response.get("error"):
            results.append({
                "model": model,
                "ranking": response.get('content', ''), # Reuse 'ranking' field for specific critique text
                "parsed_ranking": [] # No ranking in debate
            })
            
    return results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    chairman_model: str = None,
    mode: str = "standard"
):
    """
    Stage 3: Chairman synthesizes final response (streaming).
    Yields content chunks.
    """
    
    # Use provided chairman model or fallback
    active_chairman_model = chairman_model or CHAIRMAN_MODEL
    
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nFeedback: {result['ranking']}"
        for result in stage2_results
    ])
    
    if mode == "debate":
        instruction = "Synthesize a final answer by weighing the original arguments and the peer critiques. Resolve the conflicts and find the strongest truth."
        stage2_label = "STAGE 2 - Peer Critiques:"
    elif mode == "six_hats":
        instruction = "Synthesize a final answer that integrates these diverse perspectives (Hats). Ensure the final decision considers facts, feelings, risks, benefits, and creativity."
        stage2_label = "STAGE 2 - Perspective Review:"
    elif mode == "ensemble":
        stage2_text = "(Stage 2 skipped for Ensemble mode)"
        instruction = "Synthesize the provided responses into a single, high-quality answer. Identify the consensus and best insights from the ensemble."
        stage2_label = "STAGE 2 - Skipped"
    else: # standard
        instruction = "Synthesize all of this information into a single, comprehensive, accurate answer. Consider the individual responses and the peer rankings."
        stage2_label = "STAGE 2 - Peer Rankings:"

    chairman_prompt = f"""You are the Chairman of an LLM Council.
    
Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

{stage2_label}
{stage2_text}

Your task: {instruction}

Provide a clear, well-reasoned final answer:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Stream the response
    async for chunk in query_model_stream(active_chairman_model, messages):
        yield chunk
