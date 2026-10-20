"""
config/settings.py
--------------------
Single source of truth for every path, column name, and model setting
this project uses. Nothing else in the codebase should hardcode a path
or column name that belongs here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Harmonization -- dictionaries, file paths, column names
# (used by src/harmonizer/harmonizer.py and src/harmonizer/__init__.py)
# ─────────────────────────────────────────────────────────────────────────────

HARM_FILE_1 = "data/harmonization_entities.csv"
HARM_FILE_2 = "data/harmonization_time_formats.csv"

HARM_TYPE_COL = "Type"
HARM_CANONICAL_COL = "Canonical"

# NUMBER_FORMAT rows are loaded as part of the dictionary data but
# deliberately excluded from text substitution -- see harmonizer.py's own
# notes on this. Kept here, not in harmonizer.py, so a new Type category
# to skip is a one-line config change, not a code change.
HARM_SKIP_TYPES = {"NUMBER_FORMAT"}

RAW_DATASET_PATH = "data/Dataset_Raw.xlsx"
RAW_DATASET_OUTPUT_PATH = "outputs/Dataset_Harmonized.csv"
RAW_HARMONIZATION_REPORT = "outputs/dataset_harmonization_qa_report.txt"

# The free-text column that needs harmonizing. Previously the raw Excel had
# two columns both named "Conversation" (pandas renamed the second to
# "Conversation.1"), plus separate Question/Report/Commentary columns that
# were redundant copies of the same text. The dataset has been cleaned:
#   Conversation_ID  -- the conversation identifier (C1, C2, ...)
#   Conversation     -- the full turn text for every row (user + model)
# Only "Conversation" needs harmonizing.
RAW_TEXT_COLS = ["Conversation"]

# ─────────────────────────────────────────────────────────────────────────────
# Gemini API
# (used by src/llm/gemini_client.py)
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # actually your OPENROUTER key -- see src/llm/gemini_client.py
GEMINI_MODEL = "google/gemini-3.8-flash"  # routed through OpenRouter, not called directly

# Requests-per-minute cap this client self-throttles to. Kept comfortably
# under the account's real RPM limit so a burst of use doesn't trip a 429.
GEMINI_RPM = 10

GEMINI_MAX_RETRIES = 5

# ─────────────────────────────────────────────────────────────────────────────
# Similar-question search
# (used by src/search/similarity_search.py)
# ─────────────────────────────────────────────────────────────────────────────

SIMILARITY_INSTRUCTIONS_PATH = "instructions/similarity_instructions.txt"

# Per-search cap on how many matches the UI displays, even if the model
# returns more. Sorted by score, highest first -- see similarity_search.py.
MAX_RESULTS_DISPLAYED = 20

# NOTE: chunking (splitting the dataset into smaller per-call batches) was
# removed by client request -- every search now sends the full dataset in
# ONE call. This is cheaper (fewer requests against a small daily quota)
# but was found less reliable at exhaustively checking every candidate
# than the earlier chunked approach. See src/search/similarity_search.py's
# module docstring and search_similar_questions() for where this used to
# be configured (SEARCH_CHUNK_SIZE), if this ever needs reinstating.

# ─────────────────────────────────────────────────────────────────────────────
# UI -- match-strength bands and the display cutoff
# (used by app.py)
#
# MATCH_DISPLAY_FLOOR exists to describe, in the UI, the cutoff that
# instructions/similarity_instructions.txt asks Gemini to apply when
# deciding which matches to report at all. The two are independent files
# read by different parts of the app -- this constant does not change
# Gemini's behaviour -- so if one is ever changed without the other, the
# app will show a caption that no longer matches what the model was told
# to do. (This happened once already: a stale "70% or more" caption sat
# next to a model that had actually been told to use a 50% floor.) When
# changing the cutoff, update both this value and the instructions file.
MATCH_DISPLAY_FLOOR = 0.50

# (floor_percent, label, colour, description) -- checked top-down in
# app.py's band() helper; a score below the lowest floor here falls back
# to a generic "Weak match" label. Colours are Mantine colour names.
MATCH_BANDS = [
    (95, "Near-identical question", "green",
     "Same divisions, metrics, period and request, only the wording differs."),
    (85, "Same question, minor differences", "teal",
     "Asks the same thing; one detail is slightly less precise."),
    (70, "Closely related question", "yellow",
     "Same core request, but one factor (e.g. period or division list) differs."),
]

# ─────────────────────────────────────────────────────────────────────────────
# Usage / audit logging
# (used by src/usage_log.py)
#
# Every search is appended as one JSON line to a dated file under this
# directory -- see src/usage_log.py for the record format. Point this at
# a mounted volume in any deployment where the container filesystem is
# wiped on redeploy/restart, or the audit trail will not survive it.
# ─────────────────────────────────────────────────────────────────────────────

LOGS_DIR = "logs"

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# (used by src/logging_config.py, called from app.py and
# src/harmonizer/__init__.py so both the UI and a standalone harmonizer
# run get consistently formatted log output)
# ─────────────────────────────────────────────────────────────────────────────

# One of DEBUG, INFO, WARNING, ERROR, CRITICAL. DEBUG surfaces per-row detail
# (every alias substitution, every Gemini transport attempt) that is too
# noisy for normal use but useful when diagnosing a harmonization or API
# issue -- set via the LOG_LEVEL env var, no code change needed.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
