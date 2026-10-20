"""
app.py
-------
Similar Question Search -- Dash + Dash Mantine Components UI.

Designed to be self-explanatory for non-technical viewers (e.g. client
management demos):
  * a 3-step "How it works" strip at the top,
  * plain-language result headline ("3 earlier questions ask the same thing"),
  * every match labelled in words (Near-identical / Same question / Closely
    related), not just a percentage,
  * "why it matches" shown as short reason chips,
  * friendly error messages (with the technical detail tucked away).

This file is ONLY the UI layer -- all matching logic lives in
src/search/similarity_search.py's search_similar_questions(), so the UI
can be swapped out later without touching how questions are compared.

Run from PROJECT ROOT:
    python app.py
Then open http://127.0.0.1:8050
"""

import base64
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dash
import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update

from config.settings import MATCH_BANDS, MATCH_DISPLAY_FLOOR, RAW_DATASET_OUTPUT_PATH
from src.logging_config import configure_logging
from src.harmonizer import run_harmonization_raw
from src.search.similarity_search import SearchInputError, search_similar_questions
from src.usage_log import record_search

from src.llm.gemini_client import GeminiClient

configure_logging()
logger = logging.getLogger(__name__)

# On first run (no CSV yet), harmonize once so the app can start cleanly.
# After that, search_similar_questions() re-harmonizes on every search, so
# edits to data/Dataset_Raw.xlsx are picked up without restarting.
if not os.path.exists(RAW_DATASET_OUTPUT_PATH):
    logger.info("No harmonized CSV found at %s -- running harmonization...",
                RAW_DATASET_OUTPUT_PATH)
    run_harmonization_raw()


class _TrackedClient:
    """Wraps GeminiClient and records whether every Gemini call failed.

    similarity_search.py deliberately keeps going when one chunk fails, but
    if ALL chunks fail it returns an empty list -- which would look like
    "no matching question". This wrapper lets the UI tell the two apart and
    show the real error instead.
    """

    def __init__(self):
        self._client = GeminiClient()
        self.calls = 0
        self.errors = []

    def find_similar_questions(self, *args, **kwargs):
        self.calls += 1
        try:
            return self._client.find_similar_questions(*args, **kwargs)
        except Exception as e:
            self.errors.append(e)
            raise


def run_search_safely(question: str) -> list:
    client = _TrackedClient()
    matches = search_similar_questions(question, client=client)
    if client.calls and len(client.errors) == client.calls:
        raise RuntimeError(f"The Gemini search call failed, so no questions were "
                           f"compared. Last error: {client.errors[-1]}")
    return matches


# Example questions offered as one-click buttons (handy for live demos).
# (short label shown on the button, full question text)
EXAMPLES = [
    ("Cost & revenue · Wealth Management · 2025",
     "qtrs 25 give me cost and revenue for Wealth Management"),
    ("ROE vs Cost-Income · 4 divisions · Q1 2026",
     "For Q1 2026, how do CB, Markets, Asset Management, and HNW compare when it "
     "comes to equity returns? Also, does the Cost-to-Income ratio for any of these "
     "divisions look out of line with where they rank on Return on Equity?"),
    ("Strongest division overall · Q4 2025",
     "Can you compare PB, Transaction and Corporate Banking, Global Banking, and "
     "Consumer Banking for 4th Q 25 based on revenue, equity return, and CIR? "
     "Which one looks strongest overall?"),
]

# Match-strength bands and the display cutoff both live in config/settings.py
# (MATCH_BANDS, MATCH_DISPLAY_FLOOR) -- not hardcoded here -- so they can be
# retuned without touching this file, and so the cutoff shown to users can't
# silently drift out of sync with the one instructions.txt asks Gemini to use.


def band(pct: int):
    for floor, label, color, _ in MATCH_BANDS:
        if pct >= floor:
            return label, color
    return "Weak match", "gray"


THEME = {
    "primaryColor": "indigo",
    "defaultRadius": "md",
    "fontFamily": "Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    "headings": {"fontFamily": "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"},
    "components": {
        "Card": {"defaultProps": {"shadow": "sm", "withBorder": True, "radius": "lg"}},
        "Paper": {"defaultProps": {"withBorder": True, "radius": "lg"}},
        # Sentence-case badges read more naturally than Mantine's default CAPS.
        "Badge": {"defaultProps": {"tt": "none", "fw": 600}},
    },
}


def _svg_icon(paths: str, color: str = "white") -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="2.2" stroke-linecap="round" '
           f'stroke-linejoin="round">{paths}</svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


ICON_SEARCH = _svg_icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>')
ICON_CHAT = _svg_icon('<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>')
ICON_DB = _svg_icon('<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 '
                    '8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>')
ICON_LIST = _svg_icon('<path d="M9 6h11M9 12h11M9 18h11"/><path d="m3 6 1 1 2-2M3 12l1 1 2-2'
                      'M3 18l1 1 2-2"/>')


def icon(src, size=20):
    return html.Img(src=src, style={"width": f"{size}px", "height": f"{size}px"})


def split_reasons(text: str) -> list:
    """Split Gemini's reasoning ("same division (WM), same metrics (Cost and
    Revenue), same period") into short chips, ignoring commas inside
    brackets. Falls back to the full sentence if it doesn't split cleanly."""
    text = (text or "").strip()
    if not text:
        return []
    parts, cur, depth = [], "", 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch in ",;" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    parts = [p.strip(" .") for p in parts if p.strip(" .")]
    if len(parts) > 6 or any(len(p) > 90 for p in parts):
        return [text]
    return [p[0].upper() + p[1:] for p in parts]


def friendly_error(e: Exception):
    """Plain-language message for the audience + raw text for the team."""
    raw = str(e)
    low = raw.lower()
    if "api key" in low or "api_key_invalid" in low or "permission_denied" in low:
        return ("The AI service isn't set up on this computer yet.",
                "The Gemini API key is missing or not valid. Check GEMINI_API_KEY in the .env file in the "
                "project folder, then restart the app.", raw)
    if "429" in low or "resource_exhausted" in low or "quota" in low or "rate limit" in low or "rate-limit" in low:
        return ("The AI service is busy right now.",
                "The usage limit was reached. Please wait a minute and try again.", raw)
    if "is not found for api version" in low or "model" in low and "not found" in low:
        return ("The AI model name isn't recognised.",
                "Check GEMINI_MODEL in config/settings.py against the models your API key "
                "can use.", raw)
    if "not found" in low or "missing" in low or "no rows" in low:
        return ("The question history couldn't be loaded.",
                "The dataset or instructions file is missing. See the details below.", raw)
    if "connect" in low or "network" in low or "timed out" in low or "timeout" in low:
        return ("The AI service couldn't be reached.",
                "Please check the internet connection and try again.", raw)
    return ("Something went wrong while searching.",
            "Please try again. If it keeps happening, share the details below with the team.",
            raw)


# ─────────────────────────────────────────────────────────────────────────────
# Building blocks
# ─────────────────────────────────────────────────────────────────────────────

GRADIENT = {"from": "indigo", "to": "violet", "deg": 135}


def header():
    return dmc.Group(
        [
            dmc.Group(
                [
                    dmc.ThemeIcon(icon(ICON_SEARCH, 24), size=48, radius="md",
                                  variant="gradient", gradient=GRADIENT),
                    dmc.Stack(
                        [
                            dmc.Title("Similar Question Search", order=2),
                            dmc.Text("Find earlier questions that ask the same thing, even "
                                     "when they are worded differently.",
                                     size="sm", c="dimmed"),
                        ],
                        gap=2,
                    ),
                ],
                gap="md", wrap="nowrap",
            ),
            dmc.Group(
                [
                    html.Div(id="evaluator-badge"),
                    dmc.Badge("Model Evaluation Framework · MEF 1.1", variant="light",
                              size="lg", radius="sm"),
                    dmc.Switch(id="scheme-switch", size="md", onLabel="☾", offLabel="☀",
                               checked=False, **{"aria-label": "Dark mode"}),
                ],
                gap="sm",
            ),
        ],
        justify="space-between", align="center", wrap="wrap",
    )


def how_it_works():
    steps = [
        (ICON_CHAT, "1. Ask", "Type a financial question in your own words. "
                              "Abbreviations and typos are fine."),
        (ICON_DB, "2. Compare", "AI compares it with every earlier question in the "
                                "history (division, metric, period and request)."),
        (ICON_LIST, "3. Review", "See which earlier questions ask the same thing, "
                                 "with a match score and the reason."),
    ]
    return dmc.SimpleGrid(
        [
            dmc.Paper(
                dmc.Group(
                    [
                        dmc.ThemeIcon(icon(src, 18), size=38, radius="md", variant="gradient",
                                      gradient=GRADIENT),
                        dmc.Stack([dmc.Text(title, fw=700, size="sm"),
                                   dmc.Text(body, size="xs", c="dimmed")], gap=0,
                                  style={"flex": 1}),
                    ],
                    wrap="nowrap", align="flex-start", gap="sm",
                ),
                p="sm",
            )
            for src, title, body in steps
        ],
        cols={"base": 1, "sm": 3}, spacing="sm",
    )


def example_button(i: int, label: str, full: str):
    return dmc.Tooltip(
        dmc.Button(label, id={"type": "example", "index": i}, variant="light",
                   color="indigo", size="compact-sm", radius="xl", n_clicks=0),
        label=full, multiline=True, w=380, withArrow=True, openDelay=300,
    )


def search_card():
    return dmc.Card(
        [
            dmc.Text("What would you like to ask?", fw=700, size="lg"),
            dmc.Text("Write it the way a user would. The search understands different "
                     "wording, abbreviations (CIR, ROE, WM) and spelling mistakes.",
                     size="sm", c="dimmed", mb="sm"),
            dmc.Textarea(
                id="question-input",
                placeholder="e.g. Show me revenue and cost for Wealth Management in 2025",
                autosize=True, minRows=3, maxRows=8, size="md",
            ),
            dmc.Group(
                [dmc.Text("Try an example:", size="xs", c="dimmed", fw=600)]
                + [example_button(i, lbl, full) for i, (lbl, full) in enumerate(EXAMPLES)],
                gap=6, mt="sm",
            ),
            dmc.Group(
                [
                    dmc.Text("Tip: press Ctrl + Enter to search", size="xs", c="dimmed"),
                    dmc.Group(
                        [
                            dmc.Button("Clear", id="clear-button", variant="subtle",
                                       color="gray", n_clicks=0),
                            dmc.Button([icon(ICON_SEARCH, 16), html.Span("Search",
                                        style={"marginLeft": 8})],
                                       id="search-button", n_clicks=0, size="md",
                                       variant="gradient", gradient=GRADIENT),
                        ],
                        gap="xs",
                    ),
                ],
                justify="space-between", align="center", mt="md",
            ),
        ],
        padding="lg",
    )


def stat_card(label: str, value: str, hint: str, accent: str = "indigo"):
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.Text(label, size="xs", c="dimmed", fw=600, tt="uppercase"),
                dmc.Text(value, fz=28, fw=700, c=accent, lh=1.2),
                dmc.Text(hint, size="xs", c="dimmed"),
            ],
            gap=2,
        ),
        p="md",
    )


def match_card(rank: int, m: dict):
    pct = int(round(float(m.get("similarity_score", 0)) * 100))
    label, color = band(pct)
    conv = str(m.get("conversation_id", ""))
    q_num = str(m.get("question_number") or "")
    reasons = split_reasons(m.get("reasoning") or "")
    where = f"Conversation {conv}" + (f" · question {q_num.lstrip('Qq')}" if q_num else "")

    return dmc.Card(
        dmc.Group(
            [
                dmc.Stack(
                    [
                        dmc.Group(
                            [
                                dmc.Badge(f"#{rank}", variant="filled", color="dark",
                                          radius="sm"),
                                dmc.Badge(label, color=color, variant="light", radius="sm",
                                          size="lg"),
                            ],
                            gap=6,
                        ),
                        dmc.Text("Earlier question", size="xs", c="dimmed", fw=600,
                                 tt="uppercase", mt=4),
                        dmc.Text(f"“{m.get('matched_question_text', '')}”", fw=500, size="md"),
                        (dmc.Group(
                            [dmc.Text("Why it matches:", size="xs", c="dimmed", fw=600)]
                            + [dmc.Badge(r, variant="outline", color="gray", radius="xl",
                                         fw=500, size="lg") for r in reasons],
                            gap=6,
                        ) if reasons else html.Div()),
                        dmc.Tooltip(
                            dmc.Text(where, size="xs", c="dimmed", style={"cursor": "help",
                                     "width": "fit-content"}),
                            label="Where this question sits in the historical log: the "
                                  "conversation it came from, and which of that "
                                  "conversation's questions it is.",
                            multiline=True, w=280, withArrow=True,
                        ),
                    ],
                    gap=6, style={"flex": 1, "minWidth": 0},
                ),
                dmc.Stack(
                    [
                        dmc.RingProgress(
                            sections=[{"value": pct, "color": color}],
                            size=100, thickness=10, roundCaps=True,
                            label=dmc.Text(f"{pct}%", ta="center", fw=800, size="xl",
                                           c=color),
                        ),
                        dmc.Text("match", size="xs", c="dimmed", ta="center", mt=-6),
                    ],
                    gap=0, align="center",
                ),
            ],
            justify="space-between", align="center", wrap="nowrap", gap="lg",
        ),
        padding="lg", className="match-card",
    )


def skeleton_results():
    card = dmc.Card(
        dmc.Group(
            [
                dmc.Stack(
                    [dmc.Skeleton(h=22, w=200, radius="sm"), dmc.Skeleton(h=16, w="90%"),
                     dmc.Skeleton(h=14, w="60%")],
                    gap=10, style={"flex": 1},
                ),
                dmc.Skeleton(h=90, w=90, circle=True),
            ],
            wrap="nowrap",
        ),
        padding="lg",
    )
    return dmc.Stack(
        [
            dmc.Group([dmc.Loader(size="sm", type="dots"),
                       dmc.Text("Comparing your question with the full question history. "
                                "This usually takes a few seconds…", size="sm", c="dimmed")],
                      gap="xs"),
            card, card,
        ],
        gap="md",
    )


def empty_state():
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.ThemeIcon(icon(ICON_SEARCH, 22), size=46, radius="xl", variant="gradient",
                              gradient=GRADIENT),
                dmc.Text("Ask a question to see matching questions from the history",
                         fw=600, size="lg", ta="center"),
                dmc.Text("Type your own question above, or click one of the examples.",
                         c="dimmed", size="sm", ta="center"),
            ],
            align="center", gap=6,
        ),
        p="xl", style={"borderStyle": "dashed"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# App + layout
# ─────────────────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="Similar Question Search")

app.index_string = app.index_string.replace(
    "</head>",
    """<style>
      .match-card { transition: transform .15s ease, box-shadow .15s ease;
                    animation: fadeUp .35s ease both; }
      .match-card:hover { transform: translateY(-2px);
                          box-shadow: var(--mantine-shadow-md); }
      @keyframes fadeUp { from { opacity: 0; transform: translateY(6px); }
                          to   { opacity: 1; transform: none; } }
      body { background: var(--mantine-color-body); }
      /* Let long badge text wrap (e.g. on phones) instead of being cut off. */
      .mantine-Badge-root { height: auto; min-height: var(--badge-height);
                            max-width: 100%; padding-block: 2px; }
      .mantine-Badge-label { white-space: normal; overflow: visible; }
    </style></head>""",
).replace(
    "</body>",
    """<script>
      // Ctrl/Cmd + Enter in the question box starts the search.
      document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
          var b = document.getElementById('search-button');
          if (b) { e.preventDefault(); b.click(); }
        }
      });
    </script></body>""",
)

def evaluator_gate():
    """
    Modal shown on every fresh page load, before any part of the tool can
    be used. No close button and no click-outside/escape dismissal --
    typing a name is the only way through it. The name is kept in a
    session-scoped browser store (cleared when the tab is closed), and is
    attached to every search this evaluator runs so the audit log in
    LOGS_DIR can say who ran what, not just what was asked.
    """
    return dmc.Modal(
        id="evaluator-modal",
        opened=True,
        withCloseButton=False,
        closeOnClickOutside=False,
        closeOnEscape=False,
        centered=True,
        radius="lg",
        children=dmc.Stack(
            [
                dmc.Text("Before you start", fw=700, size="lg"),
                dmc.Text("Enter your name so this session can be attributed in the "
                         "usage log.", size="sm", c="dimmed"),
                dmc.TextInput(id="evaluator-name-input", label="Your name",
                              placeholder="e.g. Priya Shah", size="md"),
                dmc.Text(id="evaluator-name-error", c="red", size="xs", mih=16),
                dmc.Button("Start", id="evaluator-start-button", fullWidth=True,
                           size="md", variant="gradient", gradient=GRADIENT,
                           n_clicks=0),
            ],
            gap="sm",
        ),
    )


app.layout = dmc.MantineProvider(
    id="mantine-provider",
    theme=THEME,
    forceColorScheme="light",
    children=[
        dcc.Store(id="evaluator-store", storage_type="session"),
        evaluator_gate(),
        dmc.NotificationContainer(id="notify", position="bottom-right", autoClose=3500),
        html.Div(
            dmc.Container(
                dmc.Stack(
                    [
                        header(),
                        how_it_works(),
                        search_card(),
                        html.Div(skeleton_results(), id="loading-area",
                                 style={"display": "none"}),
                        html.Div(empty_state(), id="results-area"),
                        dmc.Text(
                            "Match scores are produced by a Gemini AI model and range from 0 to "
                            f"100%. Only matches of {int(round(MATCH_DISPLAY_FLOOR * 100))}% "
                            "or more are shown.",
                            size="xs", c="dimmed", ta="center",
                        ),
                    ],
                    gap="lg",
                ),
                size="lg", py=36,
            ),
            style={
                "minHeight": "100vh",
                "background": "radial-gradient(1200px 380px at 50% -120px, "
                              "var(--mantine-color-indigo-light), transparent)",
            },
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

@callback(Output("mantine-provider", "forceColorScheme"), Input("scheme-switch", "checked"))
def toggle_scheme(dark):
    return "dark" if dark else "light"


@callback(
    Output("evaluator-store", "data"),
    Output("evaluator-modal", "opened"),
    Output("evaluator-name-error", "children"),
    Input("evaluator-start-button", "n_clicks"),
    Input("evaluator-name-input", "n_submit"),  # lets Enter submit, not just the button
    State("evaluator-name-input", "value"),
    prevent_initial_call=True,
)
def submit_evaluator_name(_n_clicks, _n_submit, name):
    name = (name or "").strip()
    if not name:
        return no_update, True, "Please enter your name to continue."
    logger.info("Evaluator session started: %s", name)
    return name, False, ""


@callback(Output("evaluator-badge", "children"), Input("evaluator-store", "data"))
def show_evaluator_badge(name):
    if not name:
        return no_update
    return dmc.Badge(f"Evaluator: {name}", variant="outline", color="gray",
                      size="lg", radius="sm")


@callback(
    Output("question-input", "value"),
    Input({"type": "example", "index": ALL}, "n_clicks"),
    Input("clear-button", "n_clicks"),
    prevent_initial_call=True,
)
def fill_question(_examples, _clear):
    trig = ctx.triggered_id
    if trig == "clear-button":
        return ""
    if isinstance(trig, dict) and ctx.triggered[0]["value"]:
        return EXAMPLES[trig["index"]][1]
    return no_update


@callback(
    Output("results-area", "children"),
    Output("notify", "sendNotifications"),
    Input("search-button", "n_clicks"),
    Input("clear-button", "n_clicks"),
    State("question-input", "value"),
    State("evaluator-store", "data"),
    prevent_initial_call=True,
    running=[
        (Output("search-button", "loading"), True, False),
        (Output("clear-button", "disabled"), True, False),
        (Output("loading-area", "style"), {"display": "block"}, {"display": "none"}),
        (Output("results-area", "style"), {"display": "none"}, {"display": "block"}),
    ],
)
def run_search(_n, _clear, question, evaluator_name):
    def note(title, message, color):
        return [{"action": "show", "id": f"n{time.time()}", "title": title,
                 "message": message, "color": color}]

    if ctx.triggered_id == "clear-button":
        return empty_state(), no_update

    if not question or not question.strip():
        return no_update, note("Please type a question",
                               "Enter a question, or click one of the examples.", "yellow")

    # Belt-and-suspenders: the evaluator-name modal is the primary gate, but
    # a search should never be attributed to "nobody" in the audit log even
    # if the store somehow came back empty (e.g. session storage cleared
    # mid-session).
    if not evaluator_name:
        return no_update, note("Please enter your name",
                               "Reload the page and enter your name before searching.",
                               "yellow")

    asked = question.strip()
    start = time.perf_counter()
    try:
        matches = run_search_safely(asked)
    except (SearchInputError, Exception) as e:  # noqa: B014 -- same handling for both
        elapsed = time.perf_counter() - start
        title, message, raw = friendly_error(e)
        record_search(evaluator_name, asked, matches=None, elapsed_seconds=elapsed, error=raw)
        body = dmc.Alert(
            dmc.Stack(
                [
                    dmc.Text(message, size="sm"),
                    dmc.Accordion(
                        dmc.AccordionItem(
                            [dmc.AccordionControl("Technical details (for the team)"),
                             dmc.AccordionPanel(dmc.Code(raw, block=True))],
                            value="details",
                        ),
                        variant="contained", radius="md",
                    ),
                ],
                gap="sm",
            ),
            title=title, color="red", variant="light", radius="lg",
        )
        return body, note(title, message, "red")
    elapsed = time.perf_counter() - start

    record_search(evaluator_name, asked, matches=matches, elapsed_seconds=elapsed)

    if not matches:
        body = dmc.Paper(
            dmc.Stack(
                [
                    dmc.Badge("New question", color="indigo", variant="light", size="lg"),
                    dmc.Text("No earlier question asks the same thing.", fw=700, size="lg",
                             ta="center"),
                    dmc.Text("This looks like a question the system hasn't been asked before. "
                             "Try rephrasing if you expected a match.",
                             size="sm", c="dimmed", ta="center"),
                ],
                align="center", gap=6,
            ),
            p="xl",
        )
        return body, note("Search complete", f"No matching questions ({elapsed:.1f} s).",
                          "gray")

    pcts = [int(round(float(m.get("similarity_score", 0)) * 100)) for m in matches]
    top, avg = max(pcts), round(sum(pcts) / len(pcts))
    top_label, top_color = band(top)
    n = len(matches)
    headline = (f"{n} earlier question{'s' if n != 1 else ''} "
                f"ask{'s' if n == 1 else ''} the same thing")

    body = dmc.Stack(
        [
            dmc.Paper(
                dmc.Group(
                    [
                        dmc.Stack(
                            [
                                dmc.Text("Result", size="xs", c="dimmed", fw=600,
                                         tt="uppercase"),
                                dmc.Title(headline, order=3),
                                dmc.Text(f"Your question: “{asked}”", size="sm", c="dimmed"),
                            ],
                            gap=4, style={"flex": 1, "minWidth": 0},
                        ),
                        dmc.Badge(f"Best match: {top_label}", color=top_color,
                                  variant="light", size="xl", radius="sm"),
                    ],
                    justify="space-between", align="center",
                ),
                p="lg",
            ),
            dmc.SimpleGrid(
                [
                    stat_card("Matches found", str(n),
                              "Earlier questions asking the same thing"),
                    stat_card("Best match", f"{top}%",
                              "Closest earlier question",
                              top_color),
                    stat_card("Average match", f"{avg}%",
                              "Across all matches shown",
                              band(avg)[1]),
                    stat_card("Answered in", f"{elapsed:.1f} s",
                              "Compared with the full history"),
                ],
                cols={"base": 2, "md": 4}, spacing="md",
            ),
            *[match_card(i + 1, m) for i, m in enumerate(matches)],
        ],
        gap="md",
    )
    return body, note("Search complete",
                      f"{n} matching question{'s' if n != 1 else ''} found in "
                      f"{elapsed:.1f} s.", "teal")


if __name__ == "__main__":
    # debug=False hides Dash's developer toolbar, so the page looks clean in
    # demos. Set DASH_DEBUG=1 to turn it back on while developing.
    #
    # Auto-opens the app in the default browser shortly after starting --
    # the delay gives the Dash dev server a moment to actually start
    # listening before the browser tries to connect, since app.run()
    # below is blocking and the browser has to be opened from a
    # separate thread. Set DASH_NO_BROWSER=1 to skip this (e.g. if
    # running headless or the browser keeps opening a stale tab on
    # auto-reload during development).
    host = os.getenv("DASH_HOST", "127.0.0.1")
    port = int(os.getenv("DASH_PORT", "8050"))

    if os.getenv("DASH_NO_BROWSER") != "1":
        import threading
        import webbrowser

        def _open_browser():
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=_open_browser, daemon=True).start()

    app.run(debug=os.getenv("DASH_DEBUG") == "1", host=host, port=port)
