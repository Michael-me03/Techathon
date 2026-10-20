"""
tests/test_gemini_client.py
-------------------------------
Tests for src/llm/gemini_client.py: response parsing, and the
retry/backoff loop in find_similar_questions().

These deliberately do NOT make real network calls or depend on whether
the `openai` package happens to be importable in the test environment --
GeminiClient._call() (the one point where a transport is actually used)
is monkeypatched directly, so these tests exercise the retry/parsing
logic in isolation regardless of which transport (openai package vs
plain requests) this environment would normally pick.
"""

import pytest

from src.llm.gemini_client import GeminiClient, _parse_response


class TestParseResponse:
    def test_direct_json(self):
        raw = '{"matches": [{"conversation_id": "C1", "similarity_score": 0.9}]}'
        assert _parse_response(raw) == [{"conversation_id": "C1", "similarity_score": 0.9}]

    def test_json_embedded_in_surrounding_text(self):
        raw = 'Sure, here you go:\n{"matches": [{"conversation_id": "C2"}]}\nHope that helps!'
        assert _parse_response(raw) == [{"conversation_id": "C2"}]

    def test_empty_matches_is_valid(self):
        assert _parse_response('{"matches": []}') == []

    def test_truncated_response_raises_clear_error(self):
        raw = '{"matches": [{"conversation_id": "C1", "similarity_sc'
        with pytest.raises(ValueError, match="truncated"):
            _parse_response(raw)

    def test_no_json_at_all_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_response("I'm not able to help with that.")


class TestFindSimilarQuestionsRetry:
    def _client(self, monkeypatch):
        client = GeminiClient(api_key="test-key", rpm=1000)  # high rpm: don't slow the test down
        monkeypatch.setattr(client.limiter, "wait", lambda: None)  # skip real rate-limit sleeps
        monkeypatch.setattr("time.sleep", lambda _s: None)  # skip retry backoff sleeps
        return client

    def test_succeeds_on_first_try(self, monkeypatch):
        client = self._client(monkeypatch)
        monkeypatch.setattr(client, "_call", lambda messages: '{"matches": [{"conversation_id": "C1"}]}')
        result = client.find_similar_questions("q", "dataset", "instructions")
        assert result == [{"conversation_id": "C1"}]

    def test_retries_on_rate_limit_then_succeeds(self, monkeypatch):
        client = self._client(monkeypatch)
        calls = {"n": 0}

        def flaky_call(messages):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("429 rate limit exceeded")
            return '{"matches": [{"conversation_id": "C9"}]}'

        monkeypatch.setattr(client, "_call", flaky_call)
        result = client.find_similar_questions("q", "dataset", "instructions")
        assert result == [{"conversation_id": "C9"}]
        assert calls["n"] == 3

    def test_raises_after_exhausting_all_retries(self, monkeypatch):
        client = self._client(monkeypatch)

        def always_fails(messages):
            raise RuntimeError("503 unavailable")

        monkeypatch.setattr(client, "_call", always_fails)
        with pytest.raises(RuntimeError, match="API call failed"):
            client.find_similar_questions("q", "dataset", "instructions")
