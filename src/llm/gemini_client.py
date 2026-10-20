"""
src/llm/gemini_client.py
--------------------------
A minimal API wrapper for ONE thing: live similar-question search.

Talks to OpenRouter (https://openrouter.ai) via an OpenAI-compatible
/chat/completions endpoint. Two transport options are tried in order:

  1. openai package (OpenAI(base_url=..., api_key=...))
     -- used when available and working (teammate's setup).
  2. plain requests.post() fallback
     -- used automatically when the openai package is missing or broken
        (e.g. the 'proxies' conflict on certain conda environments).

The public interface (GeminiClient, find_similar_questions) is identical
in both cases -- nothing in src/search/similarity_search.py changes.

Model routed through OpenRouter: google/gemini-3.8-flash (see
config.settings.GEMINI_MODEL). GEMINI_API_KEY in .env is your
OpenRouter key.

CORE DESIGN PRINCIPLE: the model does all the interpretation. This
client hands over the raw rows as-is and trusts the instructions file
to tell the model everything it needs to know.
"""

import json
import logging
import random
import re
import time

import requests

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_RPM,
    GEMINI_MAX_RETRIES,
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_OUTPUT_TOKENS = 20000

# Try to import the openai package. If it's installed and working, use it.
# If it raises on import (wrong version, proxies conflict, etc.), fall back
# to plain requests -- detected once at import time, not on every call.
_OPENAI_CLIENT_CLASS = None
_OPENAI_UNAVAILABLE_REASON = None

try:
    from openai import OpenAI as _OpenAI
    # Smoke-test: actually instantiate it with a dummy key to catch the
    # 'proxies' conflict at import time rather than on the first real call.
    _OpenAI(base_url=OPENROUTER_BASE_URL, api_key="smoke-test")
    _OPENAI_CLIENT_CLASS = _OpenAI
    print("[gemini_client] transport: openai package")
except Exception as _e:
    _OPENAI_UNAVAILABLE_REASON = str(_e)
    print(f"[gemini_client] openai package unavailable ({_e}) "
          f"-- falling back to requests")


class RateLimiter:
    """Self-throttles calls to GEMINI_RPM requests per minute."""

    def __init__(self, rpm: int):
        self.min_interval = 60.0 / max(rpm, 1)
        self.last_call = 0.0

    def wait(self):
        elapsed = time.monotonic() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.monotonic()


SIMILARITY_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "conversation_id": {
            "type": "string",
            "description": "The Conversation ID (e.g. 'C42') of the matching row."
        },
        "question_number": {
            "type": "string",
            "description": "The Question Number label (e.g. 'Q1', 'Q2', 'Q3') shown "
                           "in brackets alongside the conversation_id for the matching "
                           "row -- e.g. if the row was shown as '[C42 Q3] ...', report "
                           "'Q3' here. A conversation contains several unrelated "
                           "questions; this identifies precisely which one matched, "
                           "since conversation_id alone is not enough."
        },
        "matched_question_text": {
            "type": "string",
            "description": "The EXACT text of the specific question within that "
                           "conversation that matched -- copy it verbatim from the "
                           "dataset. A conversation can contain several unrelated "
                           "questions; this identifies precisely which one matched, "
                           "since conversation_id alone is not enough."
        },
        "similarity_score": {
            "type": "number",
            "description": "0.0-1.0. Only genuine matches should appear here at all."
        },
        "reasoning": {
            "type": "string",
            "description": "One short phrase: what matched (topic, divisions, period)."
        }
    },
    "required": ["conversation_id", "question_number", "matched_question_text",
                 "similarity_score", "reasoning"],
    "additionalProperties": False,
}

SIMILARITY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "description": "Every row found to be a genuine match for the "
                           "new question. Empty array if none.",
            "items": SIMILARITY_MATCH_SCHEMA,
        }
    },
    "required": ["matches"],
    "additionalProperties": False,
}

_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "similarity_matches",
        "strict": True,
        "schema": SIMILARITY_RESPONSE_SCHEMA,
    },
}

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_response(raw_text: str) -> list:
    """
    Parses the model's reply into a list of match dicts. Tries a direct
    JSON parse first; falls back to extracting the first {...} block.
    Raises ValueError if no usable JSON can be found.
    """
    text = (raw_text or "").strip()
    try:
        parsed = json.loads(text)
        return parsed.get("matches", []) if isinstance(parsed, dict) else []
    except json.JSONDecodeError:
        pass

    match = _JSON_OBJECT_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return parsed.get("matches", []) if isinstance(parsed, dict) else []
        except json.JSONDecodeError:
            pass

    stripped = text.strip()
    looks_like_json_start = stripped.startswith("{") and '"matches"' in stripped[:50]
    if looks_like_json_start and not stripped.endswith("}"):
        raise ValueError(
            f"The model's reply looks truncated -- MAX_OUTPUT_TOKENS "
            f"({MAX_OUTPUT_TOKENS}) may be too low. Reply started with: {text[:200]!r}"
        )

    raise ValueError(
        f"Could not parse a JSON matches object from the model's reply: {text[:200]!r}"
    )


def _call_via_openai(client, model, messages, timeout=120) -> str:
    """Make the call using the openai package and return raw response text."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=_RESPONSE_FORMAT,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    return response.choices[0].message.content


def _call_via_requests(api_key, model, messages, timeout=120) -> str:
    """Make the call using plain requests and return raw response text."""
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "response_format": _RESPONSE_FORMAT,
            "max_tokens": MAX_OUTPUT_TOKENS,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


class GeminiClient:
    def __init__(self, api_key: str = None, model: str = None, rpm: int = None):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError(
                "No API key found. Set GEMINI_API_KEY in your .env file "
                "(this is your OpenRouter key)."
            )
        self.model = model or GEMINI_MODEL
        self.limiter = RateLimiter(rpm or GEMINI_RPM)
        self.max_retries = GEMINI_MAX_RETRIES

        # Use openai package if available, requests otherwise.
        if _OPENAI_CLIENT_CLASS is not None:
            self._openai_client = _OPENAI_CLIENT_CLASS(
                base_url=OPENROUTER_BASE_URL, api_key=self.api_key
            )
        else:
            self._openai_client = None

    def _call(self, messages: list) -> str:
        """Single transport call -- uses openai or requests depending on setup."""
        if self._openai_client is not None:
            return _call_via_openai(self._openai_client, self.model, messages)
        return _call_via_requests(self.api_key, self.model, messages)

    def find_similar_questions(self, new_question: str, dataset_rows: str,
                               instructions: str) -> list:
        """
        Send ONE new question plus the harmonized dataset to the model,
        return every genuine match found.
        """
        user_prompt = (
            f"NEW QUESTION:\n{new_question}\n\n"
            f"HISTORICAL DATASET (raw rows, each labelled [ConversationID QuestionNumber]):\n"
            f"{dataset_rows}\n\n"
            "Find every row in the historical dataset above that is a "
            "genuine match for the new question, per your instructions. "
            "For each match, return conversation_id, question_number "
            "(read directly from that row's [ConversationID QuestionNumber] "
            "label -- e.g. '[C42 Q3]' means conversation_id='C42', "
            "question_number='Q3'), the EXACT verbatim matched_question_text, "
            "similarity_score, and reasoning. Respond with ONLY the JSON "
            "object described in your response format, nothing else."
        )

        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_prompt},
        ]

        last_err = None
        for attempt in range(self.max_retries):
            self.limiter.wait()
            try:
                raw_text = self._call(messages)
                matches = _parse_response(raw_text)
                logger.info("Model returned %d match(es)", len(matches))
                for i, m in enumerate(matches, 1):
                    logger.info(
                        "  Match #%d | %s %s | Score: %.0f%% | %s",
                        i,
                        m.get("conversation_id", "?"),
                        m.get("question_number", ""),
                        float(m.get("similarity_score", 0)) * 100,
                        m.get("matched_question_text", "")[:120],
                    )
                    if m.get("reasoning"):
                        logger.info("    Reasoning: %s", m.get("reasoning"))
                return matches

            except Exception as e:
                last_err = e
                msg = str(e)
                if any(x in msg.lower() for x in (
                    "429", "rate", "resource_exhausted",
                    "503", "unavailable", "overload", "high demand",
                )):
                    backoff = (2 ** attempt) + random.uniform(1, 3)
                    print(f"[model] attempt {attempt + 1}/{self.max_retries} "
                          f"failed ({msg[:80]}) -- retrying in {backoff:.1f}s")
                    time.sleep(backoff)
                    continue
                time.sleep(2.0)

        raise RuntimeError(
            f"API call failed after {self.max_retries} attempts: {last_err}"
        )
