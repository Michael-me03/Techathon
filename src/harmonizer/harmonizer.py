"""
Core harmonization logic.

This module turns a set of "harmonization dictionaries" (CSV files that map
messy real-world phrasing to a single canonical term) into a fast, reusable
text-cleaning pipeline. It's deliberately split into small, single-purpose
functions rather than one big "do everything" function, because each step
here has failed in a different way at some point during development, and
having them separate makes it obvious which stage broke.

Pipeline, in order:
  1. load_dictionaries()   - read and merge the harmonization CSV(s)
  2. build_alias_map()     - turn the raw rows into a clean alias -> canonical dict
  3. compile_patterns()    - turn that dict into compiled regex patterns
  4. harmonize_text()      - apply those patterns to a single string
  5. harmonize_dataframe() - apply harmonize_text() across whole DataFrame columns
  6. write_qa_report()     - write out what was changed, for a human to sanity-check

None of these functions read files directly except load_dictionaries() and
harmonize_dataframe() (which takes an already-loaded DataFrame) - everything
else is a pure function that's easy to unit test in isolation.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import (
    HARM_FILE_1,
    HARM_FILE_2,
    HARM_TYPE_COL,
    HARM_CANONICAL_COL,
    HARM_SKIP_TYPES,
)

# Column names we expect to find in the harmonization CSVs. Sourced from
# config/settings.py (HARM_TYPE_COL / HARM_CANONICAL_COL) rather than typed
# inline, so that if the client ever renames a column (it's happened before),
# there's exactly one place to fix it.
logger = logging.getLogger(__name__)

TYPE_COL = HARM_TYPE_COL
CANON_COL = HARM_CANONICAL_COL

# Some entity types in the dictionary aren't meant to be substituted as plain
# text - NUMBER_FORMAT entries, for example, describe formatting rules rather
# than words to find-and-replace. Anything in this set (config/settings.py ->
# HARM_SKIP_TYPES) is loaded but ignored when we build the alias map.
SKIP_TYPES = HARM_SKIP_TYPES


# ─────────────────────────────────────────────────────────────────────────────
# 1. Load harmonization dictionaries
# ─────────────────────────────────────────────────────────────────────────────

def load_dictionaries(
    file1: str | Path = HARM_FILE_1,
    file2: str | Path = HARM_FILE_2,
) -> pd.DataFrame:
    """
    Load both harmonization CSVs and concatenate them into one DataFrame.

    Everything is read as dtype=str on purpose. If we let pandas guess types,
    a column containing values like "2025" or "Q1" can get silently parsed as
    an int or a date, and then string operations further down the pipeline
    either break or - worse - quietly produce the wrong answer. Forcing str
    up front means what we see in the CSV is exactly what we work with.

    Raises FileNotFoundError with a clearer message than the default one,
    pointing at config/settings.py, since that's almost always where the
    actual problem is (a stale path after a file got renamed or moved).
    """
    frames = []
    for path in (file1, file2):
        p = Path(path)
        try:
            df = pd.read_csv(p, dtype=str)
            logger.info("Loaded %r -> %d rows", p.name, len(df))
            frames.append(df)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Harmonization file not found: {p}\n"
                "Check HARM_FILE_1 / HARM_FILE_2 in config/settings.py."
            ) from exc

    combined = pd.concat(frames, ignore_index=True)
    logger.info("Combined: %d rows total", len(combined))
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# 2. Build alias -> canonical map
# ─────────────────────────────────────────────────────────────────────────────

def build_alias_map(harm_df: pd.DataFrame) -> dict[str, str]:
    """
    Turn the raw harmonization rows into a single dict: lowercased alias
    string -> canonical form.

    A few things worth knowing about how this works:

    - Alias columns are discovered by name pattern ("Alias1", "Alias2", ...)
      rather than hardcoded, so adding an "Alias13" column to the CSV later
      doesn't require touching this code at all.

    - Rows whose Type is in SKIP_TYPES, or that have no Canonical value, are
      silently skipped - they're not errors, just not substitution candidates.

    - If an alias is identical to its own canonical form (exact same
      string, same case), we skip it. There's no point compiling a regex
      that replaces "Revenue" with "Revenue". Note this check is
      case-SENSITIVE on purpose: a lowercase alias like "cost-income
      ratio" is NOT the same as canonical "Cost-Income Ratio" and must
      still get its own pattern, otherwise that phrase has no pattern of
      its own and inner words inside it can get hijacked by unrelated
      aliases (see harmonize_text() for how that goes wrong).

    - The important part: aliases are sorted LONGEST FIRST before we dedupe
      them into the final dict. This matters because some aliases overlap -
      e.g. "CB" might be short for one thing, while "CB rate" means something
      more specific. If we don't prioritise the longer, more specific alias,
      a short generic one can quietly win and produce the wrong replacement
      later. Processing longest-first and keeping only the first occurrence
      of each lowercased alias is the standard fix for this ("greedy
      longest-match" - the same idea used in real tokenizers).
    """
    alias_cols = [c for c in harm_df.columns if c.startswith("Alias")]

    all_types = (
        harm_df.get(TYPE_COL, pd.Series(dtype=str))
        .dropna()
        .str.strip()
        .unique()
        .tolist()
    )
    allowed_types = {t for t in all_types if t not in SKIP_TYPES}
    logger.info("Active types (%d): %s", len(allowed_types), sorted(allowed_types))

    raw_pairs: list[tuple[str, str]] = []

    for _, row in harm_df.iterrows():
        row_type = str(row.get(TYPE_COL, "")).strip()
        canonical = str(row.get(CANON_COL, "")).strip()
        if row_type not in allowed_types or not canonical:
            continue

        for ac in alias_cols:
            val = row.get(ac)
            if pd.isna(val):
                continue
            alias = str(val).strip()
            if not alias:
                continue
            # Only skip a truly no-op alias: exact same string, same case,
            # as its own canonical. Comparing case-INSENSITIVELY here was a
            # bug -- it silently dropped every alias that was just a
            # different-case spelling of the canonical (e.g. "cost-income
            # ratio" vs "Cost-Income Ratio"), which meant that exact phrase
            # never got a regex pattern at all. For single-word canonicals
            # that's harmless (nothing else touches "revenue"), but for
            # multi-word canonicals where an inner word is separately
            # aliased to something else (e.g. "income" -> "Revenue"), the
            # dropped alias left that inner word exposed to be hijacked by
            # the other alias -- "cost-income ratio" was coming out as
            # "cost-Revenue ratio".
            if alias == canonical:
                continue
            raw_pairs.append((alias, canonical))

    # Longest alias wins when two aliases would otherwise collide.
    raw_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    seen: dict[str, str] = {}
    for alias, canonical in raw_pairs:
        al = alias.lower()
        if al not in seen:
            seen[al] = canonical

    logger.info("Unique alias mappings: %d", len(seen))
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# 3. Compile regex patterns
# ─────────────────────────────────────────────────────────────────────────────

def _make_pattern(alias: str) -> re.Pattern:
    """
    Build a case-insensitive, word-boundary-aware regex for one alias.

    Two details matter here:

    - re.escape(alias) makes sure any regex-special characters that happen to
      be inside the alias text (parentheses, slashes, periods, etc.) are
      treated as literal characters, not regex syntax. Skipping this step is
      a common source of "works for 99% of aliases, then crashes on one weird
      one" bugs.

    - \\b...\\b (word boundaries) stop "IB" from matching inside "exhIBit" or
      "flexIBle". Without boundaries, short aliases in particular would match
      all sorts of unrelated substrings.

    Leading underscore means this is an internal helper - it's only ever
    called from compile_patterns() below, not meant to be imported elsewhere.
    """
    escaped = re.escape(alias)
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


def compile_patterns(
    alias_map: dict[str, str],
) -> list[tuple[re.Pattern, str, str]]:
    """
    Compile one regex pattern per alias in the map.

    Returns a list of (compiled_pattern, alias_lower, canonical) tuples
    rather than a dict, because harmonize_text() below needs to check every
    pattern against the input text - order and repeated lookups matter more
    here than keyed access.

    If a specific alias somehow produces an invalid regex (shouldn't happen
    given re.escape, but we don't assume), we skip just that one pattern and
    keep going rather than letting one bad entry take down the whole run.
    """
    patterns: list[tuple[re.Pattern, str, str]] = []
    for alias_lower, canonical in alias_map.items():
        try:
            pat = _make_pattern(alias_lower)
            patterns.append((pat, alias_lower, canonical))
        except re.error as exc:
            logger.warning("Could not compile pattern for %r: %s", alias_lower, exc)

    logger.info("Compiled %d regex patterns", len(patterns))
    return patterns


# ─────────────────────────────────────────────────────────────────────────────
# 4. Harmonize a single string
# ─────────────────────────────────────────────────────────────────────────────

def _would_duplicate_canonical(text: str, start: int, end: int, canonical: str) -> bool:
    """
    Check whether replacing text[start:end] with `canonical` would just
    reconstruct a canonical phrase that's already sitting right there in the
    source text - i.e. the alias is a prefix of its own canonical, and the
    text immediately after the match continues with the rest of that same
    canonical phrase.

    Concretely: if the alias is "Retail" and the canonical is "Retail
    Banking", and the text right after the match is " Banking", applying the
    substitution would turn "Retail Banking" into "Retail Banking Banking".
    This check catches that case before the match is ever accepted, rather
    than trying to clean up the mess afterwards.

    We only need to check the case where end < start + len(canonical),
    i.e. the matched span is shorter than the canonical itself - if the
    match is already as long as the canonical there's nothing left that
    could be duplicated.
    """
    if len(canonical) <= (end - start):
        return False

    remainder_of_canonical = canonical[end - start:]
    following_text = text[end:end + len(remainder_of_canonical)]

    return following_text.lower() == remainder_of_canonical.lower()


def harmonize_text(
    text: str,
    patterns: list[tuple[re.Pattern, str, str]],
    report_counter: Optional[dict] = None,
) -> str:
    """
    Replace every alias found in `text` with its canonical form.

    NaN values are passed straight through unchanged (pd.isna check up
    front) - this matters because model-turn rows in our conversation
    datasets often have empty Question/Report cells, and we don't want to
    turn a NaN into the literal string "nan" by accident.

    The substitution logic works in four passes:

      1. Find every match, from every pattern, anywhere in the text.
      2. Drop any match that would just reconstruct a canonical phrase
         that's already present in the text (see _would_duplicate_canonical).
         This is what stops aliases like "Retail" - a genuine prefix of its
         own canonical "Retail Banking" - from turning already-correct text
         "Retail Banking" into "Retail Banking Banking". Without this check,
         any alias that happens to be a word-boundary-respecting prefix of
         its own canonical is a silent landmine: harmless on text that uses
         the short form, corrupting on text that already uses the long form.
      3. Sort the remaining matches by position, and among matches starting
         at the same position, prefer the LONGEST one. This is the same
         longest-match principle from build_alias_map(), applied at the text
         level - if "Corporate Bank" and "Corporate" both match at the same
         spot, we want the fuller, more specific match to win.
      4. Walk through the sorted matches left to right, keeping a match only
         if it doesn't overlap with one we've already kept. This guarantees
         we never apply two overlapping substitutions to the same span of
         text, which would corrupt the string.

    Substitutions are then applied right-to-left (reversed order) so that
    replacing text at a later position doesn't shift the character offsets
    of matches earlier in the string that we haven't applied yet.

    If report_counter is supplied, every substitution actually applied gets
    logged into it as "alias -> canonical": count, which write_qa_report()
    later turns into a human-readable summary of what changed.
    """
    if pd.isna(text):
        return text

    text = str(text)

    all_matches: list[tuple[int, int, str, str]] = []
    for pat, alias_lower, canonical in patterns:
        for m in pat.finditer(text):
            if _would_duplicate_canonical(text, m.start(), m.end(), canonical):
                continue
            all_matches.append((m.start(), m.end(), canonical, alias_lower))

    if not all_matches:
        return text.strip()

    # Sort by start position; break ties by preferring the longer match.
    all_matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    chosen: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, canonical, alias_lower in all_matches:
        if start >= last_end:
            chosen.append((start, end, canonical, alias_lower))
            last_end = end

    # Apply right-to-left so earlier offsets stay valid as we edit the string.
    result = text
    for start, end, canonical, alias_lower in reversed(chosen):
        result = result[:start] + canonical + result[end:]
        if report_counter is not None:
            report_counter[f"{alias_lower} -> {canonical}"] += 1

    return result.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Harmonize a whole DataFrame
# ─────────────────────────────────────────────────────────────────────────────

def harmonize_dataframe(
    df: pd.DataFrame,
    text_cols: list[str],
    patterns: list[tuple[re.Pattern, str, str]],
    label: str,
    report_counter: dict,
) -> pd.DataFrame:
    """
    Apply harmonize_text() to each named column of a DataFrame, writing the
    result into a new "<column>_harmonized" column alongside the original.

    We deliberately keep the original column untouched and add a new one,
    rather than overwriting in place. This means anyone reviewing the output
    CSV can see the before/after side by side, which has made spotting
    harmonizer bugs and dictionary gaps much easier during QA than if the
    original text were simply gone.

    `label` is just a human-readable name (e.g. "dataset1", "Dataset_Raw")
    used in the printed progress log, so when harmonizing several files in
    one run it's clear which numbers below belong to which file.

    If a requested column doesn't exist in the DataFrame, we log a warning
    and skip it rather than raising - useful when the same harmonization
    call is reused across datasets that don't all share identical schemas.
    """
    missing = [c for c in text_cols if c not in df.columns]
    if missing:
        logger.warning("[%s] columns not found, skipping: %s", label, missing)

    out = df.copy()
    for col in text_cols:
        if col not in df.columns:
            continue
        out[col + "_harmonized"] = df[col].apply(
            lambda t: harmonize_text(t, patterns, report_counter)
        )
        changed = (out[col + "_harmonized"] != out[col].astype(str)).sum()
        logger.info("[%s] %r: %d cells changed", label, col, changed)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# 6. Write QA report
# ─────────────────────────────────────────────────────────────────────────────

def write_qa_report(
    report_counter: dict,
    output_path: Path,
) -> None:
    """
    Write out a plain-text summary of every substitution that was made,
    sorted by how often each one fired.

    This file is meant to be read by a person, not a program - it's the
    quickest way to answer "did the harmonizer actually do anything
    sensible on this run?" without having to diff two large CSVs by hand.
    A reviewer can scan the top of the list (the most common substitutions)
    and immediately tell if something looks wrong, e.g. an alias mapping to
    the wrong canonical term, or a term firing far more or less often than
    expected.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_subs = sum(report_counter.values())
    unique_pairs = len(report_counter)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("HARMONIZATION QA REPORT\n")
        fh.write("=" * 60 + "\n\n")
        fh.write(f"Total substitutions made : {total_subs}\n")
        fh.write(f"Unique alias->canonical  : {unique_pairs}\n\n")
        fh.write("Substitutions (sorted by frequency)\n")
        fh.write("-" * 60 + "\n")
        for subst, count in sorted(report_counter.items(), key=lambda x: -x[1]):
            fh.write(f"  {count:>5}x   {subst}\n")

    logger.info("Saved -> %s", output_path)
    logger.info("Total substitutions    : %d", total_subs)
    logger.info("Unique alias->canonical : %d", unique_pairs)
