"""
tests/test_similarity_search.py
-----------------------------------
Tests for src/search/similarity_search.py.

format_dataset_for_prompt() and build_raw_question_lookup() are tested
against small, hand-built DataFrames -- no file I/O, no real dataset
needed. search_similar_questions() is tested end to end against a small
FAKE harmonized dataset and a FAKE Gemini client (both monkeypatched in),
so these tests never make a real API call and never depend on -- or
mutate -- the project's real data/outputs files.
"""

import pandas as pd

from src.search.similarity_search import (
    build_raw_question_lookup,
    format_dataset_for_prompt,
    search_similar_questions,
)


def _rows(*rows):
    """rows: (Conversation_ID, Type, Question_Number, Conversation, Conversation_harmonized)"""
    return pd.DataFrame(rows, columns=[
        "Conversation_ID", "Type", "Question_Number", "Conversation", "Conversation_harmonized",
    ])


class TestFormatDatasetForPrompt:
    def test_only_user_rows_are_included(self):
        df = _rows(
            ("C1", "user", "Q1", "raw q", "harmonized q"),
            ("C1", "model", "", "raw answer", "harmonized answer"),
        )
        assert format_dataset_for_prompt(df) == ["[C1 Q1] harmonized q"]

    def test_falls_back_to_raw_conversation_when_harmonized_is_blank(self):
        df = _rows(("C2", "user", "Q1", "raw only", None))
        assert format_dataset_for_prompt(df) == ["[C2 Q1] raw only"]

    def test_rows_with_no_text_at_all_are_skipped(self):
        df = _rows(("C3", "user", "Q1", None, None))
        assert format_dataset_for_prompt(df) == []


class TestBuildRawQuestionLookup:
    def test_keys_are_case_insensitive_on_conversation_id(self):
        df = _rows(("C42", "user", "Q3", "What is the raw text?", "harmonized text"))
        lookup = build_raw_question_lookup(df)
        assert lookup[("C42", "Q3")] == "What is the raw text?"

    def test_split_question_keeps_the_longer_raw_text(self):
        # Two consecutive "user" rows sharing the same (id, question_number)
        # represent a split question -- the longer/more complete raw text
        # should win, regardless of which row appeared first.
        df = _rows(
            ("C5", "user", "Q1", "short fragment", "harmonized 1"),
            ("C5", "user", "Q1", "the full, much longer original question", "harmonized 2"),
        )
        lookup = build_raw_question_lookup(df)
        assert lookup[("C5", "Q1")] == "the full, much longer original question"


class _FakeClient:
    """Stands in for GeminiClient -- returns a fixed set of matches without
    making any real API call."""

    def __init__(self, matches):
        self._matches = matches

    def find_similar_questions(self, new_question, dataset_rows, instructions):
        return self._matches


def _small_dataset():
    return _rows(
        ("C4", "user", "Q1", "What was the raw text for C4?", "harmonized C4 text"),
        ("C34", "user", "Q1", "What was the raw text for C34?", "harmonized C34 text"),
    )


class TestSearchSimilarQuestionsWiring:
    def test_shows_raw_text_and_sorts_by_score(self, monkeypatch):
        # Skip re-harmonizing the real Dataset_Raw.xlsx, and swap in a
        # small, fixed dataset instead of the real
        # outputs/Dataset_Harmonized.csv -- this test targets the wiring
        # in search_similar_questions() itself, not the harmonizer or the
        # real dataset's contents.
        monkeypatch.setattr("src.harmonizer.run_harmonization_raw", lambda: None)
        monkeypatch.setattr(
            "src.search.similarity_search.load_harmonized_rows",
            lambda: _small_dataset(),
        )
        fake_matches = [
            {"conversation_id": "c4", "question_number": "Q1",
             "matched_question_text": "whatever gemini echoed back",
             "similarity_score": 0.80, "reasoning": "same topic"},
            {"conversation_id": "C34", "question_number": "Q1",
             "matched_question_text": "irrelevant",
             "similarity_score": 0.95, "reasoning": "near identical"},
        ]
        client = _FakeClient(fake_matches)

        results = search_similar_questions("some question", client=client)

        assert [r["conversation_id"] for r in results] == ["C34", "C4"]
        assert [r["similarity_score"] for r in results] == [0.95, 0.80]
        # The RAW conversation text is shown, not whatever Gemini echoed
        # back, and not the harmonized text either.
        assert results[1]["matched_question_text"] == "What was the raw text for C4?"
        assert results[0]["matched_question_text"] == "What was the raw text for C34?"
        assert results[1]["similarity_percentage"] == "80%"

    def test_malformed_matches_are_dropped(self, monkeypatch):
        monkeypatch.setattr("src.harmonizer.run_harmonization_raw", lambda: None)
        monkeypatch.setattr(
            "src.search.similarity_search.load_harmonized_rows",
            lambda: _small_dataset(),
        )
        client = _FakeClient([
            {"conversation_id": None, "similarity_score": 0.9},   # missing id
            {"conversation_id": "C4", "similarity_score": "bad"},  # non-numeric score
        ])
        assert search_similar_questions("q", client=client) == []
