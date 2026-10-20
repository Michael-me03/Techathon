"""
src/search/similarity_search.py
----------------------------------
The live search: one new question in, one Gemini call, matched questions
+ scores out.

CORE DESIGN PRINCIPLE -- this module does NOT merge, clean, or interpret
the dataset. It loads the raw harmonized rows and formats them as plain
text for the prompt, preserving Conversation ID, Type, and row order
exactly as they appear in the data. Recognizing patterns in that data --
including the fact that some questions are split across two consecutive
rows -- is entirely Gemini's job, guided by the instructions file at
config.settings.SIMILARITY_INSTRUCTIONS_PATH. See that file for the full
instruction text.

PROMPT NORMALIZATION -- the new question typed by the evaluator is run
through the same harmonizer (same dictionaries, same compiled patterns)
as the historical dataset before being sent to Gemini. This ensures both
sides of the comparison are in the same canonical vocabulary, so Gemini
can compare text directly without needing to resolve abbreviations or
aliases itself. The instructions file therefore contains no alias tables
or terminology reference -- that work is done deterministically here.

One search = one API call to the model (via OpenRouter), sent once
against the full dataset -- no chunking, no per-row processing, no local
pre-filtering of candidates.
"""

import logging
import os
import sys

import pandas as pd

from config.settings import (
    RAW_DATASET_OUTPUT_PATH,
    SIMILARITY_INSTRUCTIONS_PATH,
    MAX_RESULTS_DISPLAYED,
    HARM_FILE_1,
    HARM_FILE_2,
)
from src.harmonizer.harmonizer import (
    load_dictionaries,
    build_alias_map,
    compile_patterns,
    harmonize_text,
)
from src.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class SearchInputError(Exception):
    """Raised when the harmonized dataset or the instructions file is
    missing or unreadable -- checked upfront, before any Gemini call is
    made, so the UI can show a clear, fixable message rather than a raw
    stack trace."""


def load_instructions(path: str = SIMILARITY_INSTRUCTIONS_PATH) -> str:
    if not os.path.exists(path):
        raise SearchInputError(
            f"Instructions file not found: {path!r}. This file should "
            f"contain the plain-text instructions telling Gemini how to "
            f"judge similarity."
        )
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise SearchInputError(f"Instructions file at {path!r} is empty.")
    return text


def load_harmonized_rows(path: str = RAW_DATASET_OUTPUT_PATH) -> pd.DataFrame:
    """
    Loads the harmonized dataset AS-IS -- every row, in its original
    order, no merging, no filtering, no cleaning beyond what the
    harmonizer itself already did. This is deliberate: recognizing which
    rows belong together (e.g. a split question across two rows) is
    Gemini's job, not this function's.
    """
    if not os.path.exists(path):
        raise SearchInputError(
            f"Harmonized dataset not found: {path!r}. Run the harmonizer "
            f"first (src/harmonizer/__init__.py -> run_harmonization_raw())."
        )
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise SearchInputError(f"Could not read {path!r} as CSV: {e}") from e
    if df.empty:
        raise SearchInputError(f"{path!r} has no rows.")
    required = ["Conversation_ID", "Type", "Question_Number"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SearchInputError(
            f"Harmonized dataset at {path!r} is missing required column(s): "
            f"{missing}. Found columns: {list(df.columns)}"
        )
    return df


def format_dataset_for_prompt(df: pd.DataFrame, text_column: str = "Conversation_harmonized") -> list:
    """
    Formats every row as plain text for the prompt: Conversation ID,
    Question Number, and the question text, IN ORDER, exactly as they
    appear in the dataset. Rows with no text in text_column (e.g. "model"
    rows, which are answers, not questions) are skipped -- Gemini only
    needs to see the "user" rows to search for question matches, and the
    instructions file tells it to ignore anything else. Falls back to the
    raw "Conversation" column if the harmonized one is blank for a given row.

    Question Number (e.g. "Q1", "Q2", "Q3") disambiguates which of a
    conversation's several unrelated questions is being referred to --
    labelled directly in the dataset now, rather than relying on Gemini
    to quote back matching text verbatim to identify which question
    matched (the old approach -- see matched_question_text's history in
    this module).

    Deliberately does NOT merge consecutive rows or otherwise interpret
    the split-question pattern -- see module docstring. A split question
    (two consecutive "user" rows) shares the same Question Number in this
    dataset, so both lines are shown with the same label -- the
    instructions file still tells Gemini to treat same-Conversation-ID,
    same-Question-Number consecutive rows as one combined question.

    Returns a LIST of formatted lines (one per question), not a joined
    string -- see chunk_dataset_lines() below, which splits this list
    into smaller batches before each is sent to Gemini.
    """
    lines = []
    for _, row in df.iterrows():
        row_type = str(row.get("Type", "")).strip().lower()
        if row_type != "user":
            continue
        text = row.get(text_column)
        if pd.isna(text) or not str(text).strip():
            text = row.get("Conversation")
        if pd.isna(text) or not str(text).strip():
            continue
        conv_id = row.get("Conversation_ID", "")
        q_num = row.get("Question_Number", "")
        q_num_label = f" {q_num}" if q_num and not pd.isna(q_num) else ""
        lines.append(f"[{conv_id}{q_num_label}] {str(text).strip()}")
    return lines


def build_raw_question_lookup(df: pd.DataFrame, text_column: str = "Conversation_harmonized") -> dict:
    """
    Returns {(conversation_id, question_number): raw_conversation_text}.

    Gemini is only ever shown the HARMONIZED dataset (see
    format_dataset_for_prompt()), so a match's harmonized text is never
    what the evaluator should see -- this lookup lets the UI show the
    RAW conversation text instead (what was actually typed/logged originally),
    while the harmonized text is still what's used internally for
    matching.

    Keyed on (conversation_id, question_number) -- e.g. ("C9", "Q3") --
    using the dataset's own Question Number column, rather than matching
    on Gemini's echoed text. This is more reliable than the previous
    text-matching approach: Gemini is asked to report conversation_id and
    question_number directly (see gemini_client.py's response schema),
    so this lookup only needs an exact key match, not a fuzzy text
    comparison that could silently fail if Gemini paraphrases slightly.
    """
    lookup = {}
    for _, row in df.iterrows():
        row_type = str(row.get("Type", "")).strip().lower()
        if row_type != "user":
            continue
        harmonized = row.get(text_column)
        if pd.isna(harmonized) or not str(harmonized).strip():
            continue
        raw = row.get("Conversation")
        if pd.isna(raw) or not str(raw).strip():
            raw = harmonized  # fall back to harmonized if no raw text exists
        conv_id = row.get("Conversation_ID", "")
        q_num = row.get("Question_Number", "")
        if pd.isna(q_num):
            q_num = ""
        # Case-insensitive key: Gemini has been observed echoing back
        # conversation IDs in a different case than the dataset uses
        # (e.g. "c91" when the real ID is "C91") -- a case-sensitive key
        # here made the lookup silently miss in that situation, which
        # fell back to Gemini's own (sometimes wrong) matched_question_text
        # instead of the correct raw text, producing a visibly wrong
        # answer for a pair the model had actually scored correctly. The
        # key is normalized to uppercase for storage AND lookup (see the
        # call site in search_similar_questions()) so a real ID always
        # matches regardless of the case either side happens to use.
        key = (str(conv_id).strip().upper(), str(q_num).strip())
        # A split question has two consecutive rows sharing the same
        # (conversation_id, question_number) -- keep the FIRST row's raw
        # text as the representative one, don't overwrite with the
        # shorter follow-up fragment.
        if key not in lookup:
            lookup[key] = str(raw).strip()
        elif len(str(raw).strip()) > len(lookup[key]):
            # if a later row's raw text is longer (i.e. THIS row is
            # actually the main question and an earlier short fragment
            # got indexed first), prefer the longer/more complete text
            lookup[key] = str(raw).strip()
    return lookup


def search_similar_questions(new_question: str, client: GeminiClient = None) -> list:
    """
    The main entry point. Normalizes the new question through the
    harmonizer, loads the harmonized dataset and the instructions file,
    and sends the normalized question plus the ENTIRE dataset to the
    model in ONE call (no chunking -- see the client-request note at the
    call site below), returning the matches sorted by score (highest
    first), capped at MAX_RESULTS_DISPLAYED.

    Raises SearchInputError if the dataset or instructions file is
    missing/invalid, or if the API call itself fails -- checked before
    any API call is made / surfaced from the single call's own failure.

    Args:
        new_question: the evaluator's typed-in question (raw).
        client: an existing GeminiClient to reuse (e.g. from the UI's
            app-level singleton), or None to create a fresh one.

    Returns:
        list of dicts: [{conversation_id, matched_question_text,
        similarity_score, reasoning}, ...], sorted by similarity_score
        descending. Empty list if no matches were found -- not an error.
    """
    new_question = (new_question or "").strip()
    if not new_question:
        raise SearchInputError("No question was entered.")

    # Re-harmonize the dataset on every search so any edits to
    # Dataset_Raw.xlsx are always reflected immediately without restarting.
    from src.harmonizer import run_harmonization_raw
    print("[search] Re-harmonizing dataset...")
    run_harmonization_raw()

    instructions = load_instructions()
    df = load_harmonized_rows()

    # Normalize the new question through the same harmonizer pipeline used
    # on the historical dataset -- same dictionaries, same compiled patterns.
    # After this, both sides of the comparison are in the same canonical
    # vocabulary, so Gemini can compare text directly without resolving
    # abbreviations or aliases itself.
    try:
        harm_df = load_dictionaries(HARM_FILE_1, HARM_FILE_2)
        alias_map = build_alias_map(harm_df)
        patterns = compile_patterns(alias_map)
        new_question_normalized = harmonize_text(new_question, patterns)
        logger.info("New question -- original   : %s", new_question)
        logger.info("New question -- harmonized : %s", new_question_normalized)
    except Exception as e:
        # Normalization failure is non-fatal -- fall back to the raw question
        # rather than blocking the search entirely. The match quality may be
        # lower, but a search with a raw prompt is better than no search.
        print(f"[warn] Could not normalize new question: {e} -- using raw text.", file=sys.stderr)
        new_question_normalized = new_question

    all_lines = format_dataset_for_prompt(df)

    if not all_lines:
        raise SearchInputError(
            "No 'user' rows with question text were found in the harmonized "
            "dataset -- nothing to search against."
        )

    # No chunking: the full dataset is sent to the model in ONE call. This
    # is cheaper (one request per search instead of several) but was found
    # less reliable at exhaustively checking every candidate row than the
    # earlier chunked version -- see this project's own notes on that
    # tradeoff. Kept this way deliberately (client request) rather than as
    # an oversight.
    dataset_text = "\n".join(all_lines)
    client = client or GeminiClient()
    print(f"Searching {len(all_lines)} question(s) in a single call...")

    try:
        all_matches = client.find_similar_questions(new_question_normalized, dataset_text, instructions)
    except Exception as e:
        raise SearchInputError(f"The search call failed: {e}") from e

    # Defensive cleanup: keep only well-formed entries, sort, cap.
    raw_lookup = build_raw_question_lookup(df)
    clean_matches = []
    for m in all_matches:
        cid = m.get("conversation_id")
        q_num = m.get("question_number", "")
        score = m.get("similarity_score")
        if not cid or not isinstance(score, (int, float)):
            continue
        # Show the RAW question to the evaluator, not the harmonized text
        # Gemini was actually shown -- see build_raw_question_lookup().
        # Keyed on (conversation_id, question_number) now, which Gemini
        # reports directly -- far more reliable than the previous
        # approach of matching on Gemini's echoed harmonized text, which
        # could silently fail on any paraphrase. Falls back to whatever
        # text Gemini gave if the key isn't found -- better to show
        # something than nothing.
        #
        # cid is upper-cased for the lookup because Gemini has been
        # observed echoing conversation IDs back in a different case than
        # the dataset uses (e.g. "c91" for real ID "C91") -- see the same
        # note in build_raw_question_lookup(). The DISPLAYED
        # conversation_id is also normalized to this upper-cased form
        # (not whatever case Gemini happened to return), so the UI never
        # shows an inconsistent-looking ID either.
        cid_normalized = str(cid).strip().upper()
        fallback_text = m.get("matched_question_text", "")
        raw_text = raw_lookup.get((cid_normalized, str(q_num).strip()), fallback_text)
        clean_matches.append({
            "conversation_id": cid_normalized,
            "question_number": q_num,
            "matched_question_text": raw_text,
            "similarity_score": round(float(score), 3),
            "similarity_percentage": f"{round(float(score) * 100)}%",
            "reasoning": m.get("reasoning", ""),
        })

    clean_matches.sort(key=lambda m: m["similarity_score"], reverse=True)
    return clean_matches[:MAX_RESULTS_DISPLAYED]
