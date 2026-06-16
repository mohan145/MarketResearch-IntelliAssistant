# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (layer cache)
COPY pyproject.toml .
COPY src/__init__.py src/__init__.py
COPY src/backend/__init__.py src/backend/__init__.py

# Install all backend + scraping + llm deps into /install
RUN pip install --upgrade pip && \
    pip install --prefix=/install \
        "fastapi[standard]>=0.115.0" \
        "uvicorn[standard]>=0.30.0" \
        "pydantic>=2.5.0" \
        "pydantic-settings>=2.5.0" \
        "sqlalchemy>=2.0.0" \
        "python-jose[cryptography]>=3.3.0" \
        "bcrypt>=4.0.0" \
        "sse-starlette>=2.1.0" \
        "httpx>=0.27.0" \
        "trafilatura>=1.12.0" \
        "lxml[html-clean]>=4.9.0" \
        "langchain-core>=0.3.0" \
        "langchain-google-genai>=2.0.0" \
        "langchain-anthropic>=0.3.0" \
        "langchain-openai>=0.2.0" \
        "jinja2>=3.1.0" \
        "python-dotenv>=1.0.0"

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create data directory as mount point for Azure File Share
RUN mkdir -p /app/data

# Copy application source
COPY src/ src/

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]