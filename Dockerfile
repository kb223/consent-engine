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

# Install Python dependencies (cached layer)
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Install Playwright Chromium browser only
RUN uv run playwright install chromium

# Copy application source
COPY src/ src/
COPY data/ data/
COPY templates/ templates/

ENV PYTHONPATH=/app/src

EXPOSE 8080

# Default: HTTP API. Use `docker run consent-engine consent-engine audit <url>`
# for CLI mode.
CMD ["uv", "run", "uvicorn", "consent_engine.api:app", "--host", "0.0.0.0", "--port", "8080"]
