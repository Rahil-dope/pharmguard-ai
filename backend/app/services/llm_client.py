"""
Minimal LLM wrapper: OpenAI ChatCompletion when OPENAI_API_KEY is set;
otherwise deterministic fallback for disambiguation and chain-of-thought.
"""
import os
import re
from typing import Optional

# Optional OpenAI
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DISAMBIGUATION_THRESHOLD = 60


def _client():
    """Return OpenAI client if key present, else None."""
    if OPENAI_API_KEY and OpenAI:
        return OpenAI(api_key=OPENAI_API_KEY)
    return None


def disambiguate(user_text: str, candidates: list[dict], top_k: int = 5) -> dict:
    """
    If fuzzy match confidence was low, ask LLM to pick from candidates or ask clarifying question.
    candidates: list of {"id", "name", "brand", "score"}.
    Returns: {"selected_id": str or None, "message": str, "cot": str}.
    """
    client = _client()
    top = candidates[:top_k]
    if not client or not top:
        # Fallback: pick best score if any
        if top:
            return {
                "selected_id": top[0].get("id"),
                "message": f"Best match: {top[0].get('name', '')}",
                "cot": "No LLM; used best fuzzy match.",
            }
        return {"selected_id": None, "message": "Could not identify medicine. Please specify name or brand.", "cot": "No candidates."}

    prompt = f"""You are a pharmacy assistant. The user said: "{user_text}"

Available medicines (id, name, brand):
{chr(10).join(f"- {c.get('id')}: {c.get('name')} ({c.get('brand')})" for c in top)}

Reply with exactly one line: either "ID:<id>" to select (e.g. ID:med_aspirin_75), or "ASK:<short clarifying question>".
Then on the next line give a one-sentence chain-of-thought explanation."""

    try:
        model_name = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        content = (resp.choices[0].message.content or "").strip()
        cot = content
        selected_id = None
        message = "Please clarify which medicine you need."
        for line in content.split("\n"):
            line = line.strip()
            if line.upper().startswith("ID:"):
                raw = line[3:].strip()
                for c in top:
                    if c.get("id") == raw:
                        selected_id = raw
                        message = f"Selected: {c.get('name', raw)}"
                        break
                break
            if line.upper().startswith("ASK:"):
                message = line[4:].strip()
                break
        return {"selected_id": selected_id, "message": message, "cot": cot}
    except Exception as e:
        if top:
            return {
                "selected_id": top[0].get("id"),
                "message": f"Using best match: {top[0].get('name', '')}",
                "cot": f"LLM error fallback: {e!s}",
            }
        return {"selected_id": None, "message": "Could not identify medicine.", "cot": str(e)}


def chain_of_thought(user_text: str, nlu_slots: dict, decision: str, action: str) -> str:
    """
    Ask the model for a short step-by-step reasoning (CoT) to store in trace.
    If no API key, return a deterministic summary.
    """
    client = _client()
    if not client:
        return (
            f"Input: {user_text}. NLU: {nlu_slots}. Decision: {decision}. Action: {action}."
        )

    prompt = f"""In 2-3 short sentences, explain the reasoning for this pharmacy decision:
User said: "{user_text}"
Extracted: {nlu_slots}
Decision: {decision}
Action: {action}

Provide step-by-step reasoning only, no bullet points."""

    try:
        model_name = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return f"Decision: {decision}. Action: {action}. (LLM CoT failed: {e!s})"
