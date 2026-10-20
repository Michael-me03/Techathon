"""
tests/test_harmonizer.py
---------------------------
Unit tests for the harmonization pipeline (src/harmonizer/harmonizer.py).

Two kinds of test here, deliberately kept separate:

  * Pure unit tests, built on small in-memory DataFrames rather than the
    real CSVs. These target the *logic* itself (case-sensitivity of the
    self-skip check, longest-alias-wins, duplicate-canonical guarding) and
    keep passing even if the real dictionaries change shape.

  * Regression tests against the REAL data/harmonization_entities.csv.
    These exist because two specific bugs were fixed once, then silently
    reintroduced when the CSV was later expanded from an older base copy
    (see README.md -> Known issues). A unit test alone would not catch
    that kind of regression, because the bug lives in the data file, not
    in harmonizer.py -- these tests exist specifically to catch it
    happening a third time.
"""

import pandas as pd
import pytest

from config.settings import HARM_FILE_1, HARM_FILE_2
from src.harmonizer.harmonizer import (
    build_alias_map,
    compile_patterns,
    harmonize_text,
    load_dictionaries,
)


def _df(rows):
    """Build a harmonization-dictionary-shaped DataFrame from a list of
    (Type, Canonical, [aliases...]) tuples."""
    max_aliases = max(len(r[2]) for r in rows)
    records = []
    for row_type, canonical, aliases in rows:
        record = {"Type": row_type, "Canonical": canonical}
        for i in range(max_aliases):
            record[f"Alias{i + 1}"] = aliases[i] if i < len(aliases) else None
        records.append(record)
    return pd.DataFrame(records)


class TestBuildAliasMapCaseSensitivity:
    """Regression tests for the case-insensitive self-skip bug: comparing
    alias.lower() == canonical.lower() silently dropped any alias that was
    only a different-case spelling of its own canonical, which left inner
    words of multi-word canonicals exposed to being hijacked by unrelated
    aliases (e.g. "cost-income ratio" -> "cost-Revenue ratio")."""

    def test_lowercase_alias_of_multiword_canonical_is_kept(self):
        df = _df([
            ("FINANCIAL_TERM", "Cost-Income Ratio", ["cost-income ratio", "CIR"]),
            ("FINANCIAL_TERM", "Revenue", ["income"]),
        ])
        alias_map = build_alias_map(df)
        assert alias_map.get("cost-income ratio") == "Cost-Income Ratio"

    def test_full_pipeline_does_not_hijack_inner_word(self):
        # This is the bug as it manifested end to end: without the fix,
        # "cost-income ratio" had no pattern of its own, so the
        # separately-aliased word "income" -> "Revenue" fired inside it.
        df = _df([
            ("FINANCIAL_TERM", "Cost-Income Ratio", ["cost-income ratio", "CIR"]),
            ("FINANCIAL_TERM", "Revenue", ["income"]),
        ])
        alias_map = build_alias_map(df)
        patterns = compile_patterns(alias_map)
        result = harmonize_text("what is the cost-income ratio for WM", patterns)
        assert "Cost-Income Ratio" in result
        assert "cost-Revenue ratio" not in result

    def test_exact_same_string_same_case_is_skipped(self):
        # A truly no-op alias (identical string, identical case) should not
        # get its own pattern -- there is nothing to substitute.
        df = _df([("FINANCIAL_TERM", "Revenue", ["Revenue", "income"])])
        alias_map = build_alias_map(df)
        assert "revenue" not in alias_map
        assert alias_map.get("income") == "Revenue"


class TestBuildAliasMapLongestWins:
    def test_longer_more_specific_alias_beats_shorter_generic_one(self):
        df = _df([
            ("DIVISION", "Corporate Banking", ["CB", "Corporate Bank"]),
            ("FINANCIAL_TERM", "Central Bank Rate", ["CB rate"]),
        ])
        alias_map = build_alias_map(df)
        patterns = compile_patterns(alias_map)
        assert harmonize_text("what is the CB rate today", patterns) == \
            "what is the Central Bank Rate today"
        assert harmonize_text("show me CB revenue", patterns) == \
            "show me Corporate Banking revenue"


class TestHarmonizeTextDuplicateGuard:
    def test_does_not_duplicate_canonical_when_alias_is_a_prefix_of_it(self):
        df = _df([("DIVISION", "Retail Banking", ["Retail"])])
        alias_map = build_alias_map(df)
        patterns = compile_patterns(alias_map)
        # "Retail" is a prefix of its own canonical "Retail Banking" -- text
        # that already reads "Retail Banking" must not become
        # "Retail Banking Banking".
        assert harmonize_text("Retail Banking revenue", patterns) == "Retail Banking revenue"

    def test_short_form_still_gets_expanded(self):
        df = _df([("DIVISION", "Retail Banking", ["Retail"])])
        alias_map = build_alias_map(df)
        patterns = compile_patterns(alias_map)
        assert harmonize_text("Retail revenue", patterns) == "Retail Banking revenue"


@pytest.fixture(scope="module")
def real_patterns():
    """Compiled patterns from the ACTUAL data/harmonization_entities.csv +
    data/harmonization_time_formats.csv -- built once per test module
    since compiling ~4,000 patterns on every test would be wasteful."""
    harm_df = load_dictionaries(HARM_FILE_1, HARM_FILE_2)
    alias_map = build_alias_map(harm_df)
    return compile_patterns(alias_map)


class TestRealDictionaryRegressions:
    """These load the ACTUAL data/harmonization_entities.csv. They exist to
    catch the specific bugs that were fixed once and then silently
    reintroduced when the CSV was expanded from an older base copy -- see
    README.md -> Known issues. If either of these starts failing, someone
    has edited/replaced harmonization_entities.csv from a copy missing
    these fixes."""

    def test_hyphenated_cost_to_income_ratio_is_recognized(self, real_patterns):
        result = harmonize_text("what is the cost-to-income ratio for WM", real_patterns)
        assert "Cost-Income Ratio" in result

    def test_where_is_not_over_aggressively_mapped_to_filter(self, real_patterns):
        # "where" alone is too generic a word to safely mean the FILTER
        # action -- it appears in ordinary questions ("where is the
        # revenue for CB") that have nothing to do with filtering.
        result = harmonize_text("where is the revenue for CB", real_patterns)
        assert "Filter" not in result
