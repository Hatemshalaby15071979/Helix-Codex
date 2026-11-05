#!/usr/bin/env sh
# Resolve the headless API dependency closure against the canonical full lock.
# The constraint preserves package versions; --generate-hashes pins artifacts.
set -eu

cd "$(dirname "$0")/.."
exec uv pip compile \
  --python-version 3.12 \
  --generate-hashes \
  --constraint release/requirements.lock.txt \
  --output-file release/requirements-api.lock.txt \
  release/requirements-api.in
