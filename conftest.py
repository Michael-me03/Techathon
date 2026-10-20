"""
Root-level conftest.py.

Empty on purpose -- its only job is to give pytest a file to anchor at
the project root when it works out each test file's import path (pytest's
default "prepend" import mode walks up from a test file to the nearest
directory *without* an __init__.py and inserts that directory at the
front of sys.path). Because this file lives at the project root, that
walk stops here, so `import config.settings`, `import src...` and
`import app` all resolve exactly the way they do when running
`python app.py` directly -- no separate sys.path hacking needed in the
tests themselves.
"""
