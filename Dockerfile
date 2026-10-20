# Similar Question Search -- Frontend-only container.
#
# This app calls out to OpenRouter for all model inference and does no
# local GPU work, so per the university Data Lab's deployment guide it only
# needs the Frontend / Non-GPU path: one Docker container running the Dash
# UI, deployed to Portainer. No Backend notebook, GPU, or LocalTunnel /
# Cloudflare Tunnel is needed -- see README.md -> Deploying.

# Pinned to an exact Python patch version rather than a floating "3.12-slim"
# tag, so a rebuild months from now can't silently pick up a different
# Python patch release and behave differently in production than it did
# when this was tested.
FROM python:3.12.7-slim

WORKDIR /app

# Install dependencies in their own layer, before copying the rest of the
# source, so `docker build` only re-installs packages when
# requirements.txt actually changes -- not on every source-code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user rather than root. UID/GID 1000 is used
# explicitly (not just `useradd`'s default) so it's predictable if a host
# volume needs matching ownership -- see README.md -> Deploying for what to
# do if a mounted logs/ or outputs/ folder shows permission errors.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser \
    && mkdir -p /app/logs /app/outputs \
    && chown -R appuser:appuser /app
USER appuser

ENV DASH_HOST=0.0.0.0
ENV DASH_PORT=8050
ENV DASH_NO_BROWSER=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8050

# Basic liveness check -- uses Python's own stdlib (no curl/wget installed
# in the slim image) to confirm the Dash server is actually accepting
# connections, not just that the process is running.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('DASH_PORT', '8050'), timeout=3)" || exit 1

CMD ["python", "app.py"]
