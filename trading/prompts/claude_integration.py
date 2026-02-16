"""
Claude API integration for the trading agent.
Uses your Claude Pro subscription via the Anthropic API.
Model priority: Opus 4 > Sonnet 4.5 > Haiku (for cheaper tasks).
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("claude_integration")

# Model priority
MODELS = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}


def get_client():
    """Get Anthropic client. Requires ANTHROPIC_API_KEY in .env."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("Install anthropic SDK: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not set. Add it to trading/.env\n"
            "Get your key from: https://console.anthropic.com/settings/keys"
        )
    return anthropic.Anthropic(api_key=api_key)


def ask_claude(
    prompt: str,
    system_prompt: str = None,
    model_tier: str = "sonnet",
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Send a prompt to Claude and get a response.

    model_tier: "opus" for complex reasoning, "sonnet" for general tasks, "haiku" for simple/cheap tasks
    """
    client = get_client()
    model = MODELS.get(model_tier, MODELS["sonnet"])

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)
    return response.content[0].text


def ask_claude_for_strategy(user_request: str) -> Dict[str, Any]:
    """
    Ask Claude to create a strategy config from a natural language request.
    Uses Opus for complex strategy design.
    """
    from trading.prompts.system_prompt import STRATEGY_CREATION_PROMPT, TRADING_AGENT_SYSTEM_PROMPT

    prompt = STRATEGY_CREATION_PROMPT.format(user_request=user_request)
    response = ask_claude(
        prompt=prompt,
        system_prompt=TRADING_AGENT_SYSTEM_PROMPT,
        model_tier="opus",
        max_tokens=4096,
    )

    # Extract JSON from response
    try:
        # Try to find JSON in the response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    logger.warning("Could not parse strategy JSON from Claude response")
    return {"raw_response": response}


def analyze_backtest_results(results: Dict[str, Any]) -> str:
    """
    Ask Claude to analyze backtest results and suggest improvements.
    Uses Sonnet for cost-effective analysis.
    """
    from trading.prompts.system_prompt import BACKTEST_PROMPT

    prompt = BACKTEST_PROMPT.format(results=json.dumps(results, indent=2))
    return ask_claude(
        prompt=prompt,
        model_tier="sonnet",
        max_tokens=2048,
    )


def review_pine_script(script: str) -> str:
    """
    Ask Claude to review generated Pine Script for correctness.
    Uses Haiku for this quick validation task.
    """
    from trading.prompts.system_prompt import PINE_SCRIPT_REVIEW_PROMPT

    prompt = PINE_SCRIPT_REVIEW_PROMPT.format(script=script)
    return ask_claude(
        prompt=prompt,
        model_tier="haiku",
        max_tokens=4096,
    )


def chat(
    message: str,
    conversation_history: Optional[List[Dict]] = None,
    model_tier: str = "sonnet",
) -> tuple:
    """
    Multi-turn chat with the trading agent.
    Returns (response_text, updated_history).
    """
    from trading.prompts.system_prompt import TRADING_AGENT_SYSTEM_PROMPT

    client = get_client()
    model = MODELS.get(model_tier, MODELS["sonnet"])

    if conversation_history is None:
        conversation_history = []

    conversation_history.append({"role": "user", "content": message})

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=TRADING_AGENT_SYSTEM_PROMPT,
        messages=conversation_history,
        temperature=0.3,
    )

    assistant_msg = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_msg})

    return assistant_msg, conversation_history
