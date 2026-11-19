# syntax=docker/dockerfile:1
# Multi-stage build: dependencies in a builder stage, runtime image carries
# only site-packages + source — smaller surface, no build tooling in prod.

FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[api]"

FROM python:3.12-slim AS runtime
WORKDIR /app
# Non-root user (ADR: security baseline)
RUN groupadd --system app && useradd --system --gid app app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src ./src
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1
CMD ["python", "-m", "uvicorn", "pfpro.api:app", "--host", "0.0.0.0", "--port", "8080"]
