FROM python:3.12-slim

# System deps required by Playwright Chromium
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies (cached layer). README.md is required because
# pyproject.toml declares `readme = "README.md"` — without it any `uv run`
# that builds the project fails with "Readme file does not exist".
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source BEFORE the playwright step. `uv run` below installs
# the project (it was skipped above via --no-install-project), which needs
# both src/ and README.md present. The vendor library (data/) and Jinja2
# templates/ live under src/consent_engine/, so this single COPY brings them
# in too.
COPY src/ src/

# Install Playwright Chromium browser only.
RUN uv run playwright install chromium

ENV PYTHONPATH=/app/src

EXPOSE 8080

# Default: HTTP API. Use `docker run consent-engine consent-engine audit <url>`
# for CLI mode.
CMD ["uv", "run", "uvicorn", "consent_engine.api:app", "--host", "0.0.0.0", "--port", "8080"]
