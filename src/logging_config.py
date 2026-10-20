"""
src/logging_config.py
------------------------
One place to turn on logging for the whole app, so every module's
logger.info() / logger.warning() calls (app.py, the harmonizer, the
Gemini client, the search module) actually produce visible, consistently
formatted output -- regardless of which entry point started the process
(the Dash app, the harmonizer run standalone from the command line, or
a pytest run).

configure_logging() is safe to call more than once: logging.basicConfig()
is a documented no-op once the root logger already has a handler, so
only the FIRST call in a process actually takes effect. This lets both
app.py and src/harmonizer/__init__.py call it unconditionally without
either one worrying about duplicate log lines.

Verbosity is controlled by the LOG_LEVEL environment variable (see
config/settings.py) rather than hardcoded here, so a deployment can turn
on DEBUG-level detail (e.g. every alias substitution, every Gemini
transport attempt) without a code change.
"""

import logging

from config.settings import LOG_LEVEL

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s %(name)s: %(message)s"


def configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(level=level, format=_LOG_FORMAT)
