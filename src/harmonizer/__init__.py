"""
Public entry point for the harmonizer package.

Everything a caller needs is exposed from here: the individual building
blocks re-exported from harmonizer.py (in case someone wants to call them
directly, e.g. from a notebook or a test), plus one high-level function,
run_harmonization_raw(), that runs the whole pipeline end to end against
our one real input file, Dataset_Raw.xlsx.

Why a separate __init__.py instead of putting this in harmonizer.py?
harmonizer.py is the "library" - pure functions, no knowledge of specific
file paths or which columns belong to which dataset. This file is the
"application" - it knows about our actual project layout (where the data
lives, what the output should be called) and wires the library functions
together into something you can just call and walk away from.
"""

from __future__ import annotations

from collections import defaultdict
import logging
import os
import pathlib

import pandas as pd

from config.settings import (
    HARM_FILE_1,
    HARM_FILE_2,
    RAW_DATASET_PATH,
    RAW_DATASET_OUTPUT_PATH,
    RAW_HARMONIZATION_REPORT,
    RAW_TEXT_COLS,
)

from .harmonizer import (
    load_dictionaries,
    build_alias_map,
    compile_patterns,
    harmonize_text,
    harmonize_dataframe,
    write_qa_report,
)
from src.logging_config import configure_logging

logger = logging.getLogger(__name__)

__all__ = [
    "load_dictionaries",
    "build_alias_map",
    "compile_patterns",
    "harmonize_text",
    "harmonize_dataframe",
    "write_qa_report",
    "assign_question_numbers",
    "run_harmonization_raw",
]

# The single "Conversation" column holds the full turn text for every row
# (both user questions and model responses). It is the only column that needs
# harmonizing. The old dataset had duplicate "Conversation" columns (pandas
# renamed the second to "Conversation.1") plus separate Question / Report /
# Commentary columns -- all redundant copies of the same text, now removed.
#
# The actual list (RAW_TEXT_COLS) lives in config/settings.py, imported
# above, so which columns get harmonized is a one-line config change rather
# than a code change.


def assign_question_numbers(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Add a 'Question_Number' column (Q1, Q2, Q3, ...) to the dataframe,
    derived purely from row order within each conversation.

    Rules:
      - Only 'user' rows get a Question_Number; model rows get an empty string.
      - The counter increments each time a new user row appears after a
        non-user row (i.e. after the model responded).
      - Two consecutive user rows sharing the same Conversation_ID are a
        SPLIT QUESTION -- the second row is a short follow-up sent before
        the model replied. Both rows get the SAME Question_Number so Gemini
        sees them as one combined question.

    Example for a conversation with a split on Q3:
        user  -> Q1
        model ->
        user  -> Q2
        model ->
        user  -> Q3   (main question)
        user  -> Q3   (split follow-up, consecutive user row)
        model ->

    This column is what makes the [ConversationID QuestionNumber] labels
    in the prompt real rather than Gemini-inferred. Without it, Gemini was
    guessing Q-numbers from position -- correct most of the time but
    unreliable across chunk boundaries.
    """
    q_numbers = []
    # Track state per conversation so the counter resets for each one.
    conv_counter: dict = {}   # Conversation_ID -> current Q number
    conv_prev_type: dict = {} # Conversation_ID -> type of previous row

    for _, row in df.iterrows():
        cid = str(row.get("Conversation_ID", "")).strip()
        row_type = str(row.get("Type", "")).strip().lower()

        if row_type == "user":
            prev_type = conv_prev_type.get(cid)
            if prev_type == "user":
                # Consecutive user row = split question, reuse current number
                q_num = conv_counter.get(cid, 1)
            else:
                # New question -- increment counter
                q_num = conv_counter.get(cid, 0) + 1
                conv_counter[cid] = q_num
            q_numbers.append(f"Q{q_num}")
        else:
            q_numbers.append("")

        conv_prev_type[cid] = row_type

    df = df.copy()
    df.insert(df.columns.get_loc("Type") + 1, "Question_Number", q_numbers)

    user_count = sum(1 for q in q_numbers if q)
    logger.info("Assigned Question_Number to %d user rows across %d conversations.",
                user_count, len(conv_counter))
    return df


def run_harmonization_raw() -> None:
    """
    Run the full harmonization pipeline against Dataset_Raw.xlsx and write
    the result to outputs/Dataset_Harmonized.csv.

    Steps:
      1. Load both harmonization dictionaries (entities + time formats).
      2. Build the alias map and compile it into regex patterns.
      3. Load Dataset_Raw.xlsx, assign Question_Number, then harmonize
         the Conversation column.
      4. Write a plain-text QA report summarising what was changed.

    The output is deliberately saved as .csv, not .xlsx - a CSV is easier to
    diff, easier to load into pandas/Excel/anything else downstream, and
    avoids carrying Excel-specific quirks (merged cells, formatting, multiple
    sheets) into what's meant to be a clean, flat dataset.

    If Dataset_Raw.xlsx isn't where config/settings.py says it should be,
    this logs a clear SKIP warning and moves on to writing the (empty) QA
    report, rather than crashing the whole run. That's a deliberate choice -
    in a pipeline that might one day process several files in sequence, one
    missing file shouldn't take down everything after it.
    """
    configure_logging()

    SEP = "=" * 60
    DASH = "-" * 60

    out_path = pathlib.Path(RAW_DATASET_OUTPUT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(SEP)
    logger.info("Step 1 of 4 - Loading harmonization dictionaries")
    logger.info(SEP)

    harm_df = load_dictionaries(HARM_FILE_1, HARM_FILE_2)

    logger.info("Step 2 of 4 - Building alias map")
    logger.info(DASH)

    alias_map = build_alias_map(harm_df)
    patterns = compile_patterns(alias_map)

    logger.info("Step 3 of 4 - Harmonizing Dataset_Raw")
    logger.info(DASH)

    report_counter: dict = defaultdict(int)

    try:
        df = pd.read_excel(RAW_DATASET_PATH, dtype=str)
        logger.info("Loaded %s -> %d rows, %d columns", os.path.basename(RAW_DATASET_PATH), len(df), len(df.columns))
        logger.debug("Columns: %s", list(df.columns))

        # Excel stores date-only cells as full datetimes internally (midnight
        # time component included). Reading with dtype=str turns that into a
        # string like "2025-01-01 00:00:00" instead of just "2025-01-01".
        # Strip the time portion here so the output Date column matches what
        # the source file actually intended to represent - the harmonizer
        # itself never touches this column, so this fix belongs at load time,
        # not inside harmonize_dataframe().
        if "Date" in df.columns:
            df["Date"] = df["Date"].str.replace(r"\s+00:00:00$", "", regex=True)

        # Assign Question_Number before harmonizing so it is present in the
        # output CSV. This is what makes [ConversationID QuestionNumber]
        # labels in the search prompt real rather than Gemini-inferred.
        df = assign_question_numbers(df)

        df_out = harmonize_dataframe(df, RAW_TEXT_COLS, patterns, "Dataset_Raw", report_counter)
        df_out.to_csv(out_path, index=False)
        logger.info("Saved -> %s", out_path)
    except FileNotFoundError:
        logger.warning("SKIP: %s not found.", RAW_DATASET_PATH)

    logger.info("Step 4 of 4 - Writing QA report")
    logger.info(DASH)

    write_qa_report(report_counter, pathlib.Path(RAW_HARMONIZATION_REPORT))

    logger.info(SEP)
    logger.info("Harmonization complete.")
    logger.info(SEP)
