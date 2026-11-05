# Helix Codex OS — local-first enterprise runtime (C8)
#
# Headless API runtime image. Cockpit and development dependencies stay in the
# builder/test environment; /data remains the durable tenant-isolated volume.

FROM python:3.12.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt requirements-dev.txt pyproject.toml ./
COPY release/requirements.lock.txt release/requirements-api.lock.txt release/
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install -r release/requirements.lock.txt

COPY . .
RUN mkdir -p /dist \
    && /opt/venv/bin/pip wheel --no-deps --no-build-isolation --wheel-dir /dist .

FROM python:3.12.10-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HELIX_ENV=local \
    HELIX_ROOT=/app \
    HELIX_DB_PATH=/data/workflow.db \
    HELIX_AUDIT_DB_PATH=/data/audit.db \
    HELIX_SAMPLE_DATA_MODE=false \
    OLLAMA_HOST=http://ollama:11434 \
    HELIX_OLLAMA_ACCELERATOR=auto

COPY release/requirements-api.lock.txt /tmp/requirements-api.lock.txt

# Upgrade OS packages so the Trivy image scan (HIGH/CRITICAL) starts from
# current Debian security fixes rather than the base image's snapshot.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 helix \
    && mkdir -p /app /data \
    && chown -R helix:helix /app /data \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements-api.lock.txt \
    && rm /tmp/requirements-api.lock.txt

COPY --from=builder /dist/ /tmp/wheels/
RUN /opt/venv/bin/pip install --no-cache-dir --no-deps /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels
WORKDIR /app
COPY --from=builder --chown=helix:helix /build/organization/role-catalog.yaml /app/organization/role-catalog.yaml
COPY --from=builder --chown=helix:helix /build/organization/capability-registry.yaml /app/organization/capability-registry.yaml
COPY --from=builder --chown=helix:helix /build/alembic.ini /app/alembic.ini
COPY --from=builder --chown=helix:helix /build/migrations /app/migrations

# The entrypoint initializes SQLite schemas before the API starts. The process
# stays unprivileged; /data is writable and the Compose runtime keeps the root
# filesystem read-only.
COPY --chown=helix:helix infra/docker/entrypoint.sh /usr/local/bin/helix-entrypoint
RUN chmod 0555 /usr/local/bin/helix-entrypoint

USER helix
WORKDIR /data
VOLUME ["/data"]
EXPOSE 8000

# Component-level health (control-plane, registries, filesystem; Ollama
# optional). This is neither the liveness probe (GET /healthz: process alive,
# no storage touch) nor the readiness probe (GET /readyz: workflow store
# reachable plus audit store present, readable, and chain-verified, else 503).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python scripts/health_check.py --db-path "$HELIX_DB_PATH" || exit 1

ENTRYPOINT ["/usr/local/bin/helix-entrypoint"]
CMD ["uvicorn", "server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
