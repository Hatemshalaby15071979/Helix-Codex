"""Security invariants for the supported Docker Compose API deployment."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_api_compose_ports_are_bound_to_loopback() -> None:
    compose = yaml.safe_load((ROOT / "infra/docker/docker-compose.yml").read_text())
    services = compose["services"]
    assert services["helix-api"]["ports"] == ["127.0.0.1:8000:8000"]
    assert services["helix"]["ports"] == ["127.0.0.1:8501:8501"]


def test_api_compose_requires_a_secret_and_tenant_scope() -> None:
    compose = yaml.safe_load((ROOT / "infra/docker/docker-compose.yml").read_text())
    environment = compose["services"]["helix-api"]["environment"]
    assert environment["HELIX_API_TOKEN"].startswith("${HELIX_API_TOKEN:?")
    assert environment["HELIX_API_TOKEN_TENANT_ID"].startswith("${HELIX_API_TOKEN_TENANT_ID:?")
    assert environment["HELIX_API_ALLOW_GLOBAL_OPERATOR"] == "false"


def test_compose_images_can_be_pinned_for_rollback() -> None:
    api = yaml.safe_load((ROOT / "infra/docker/docker-compose.yml").read_text())
    app = yaml.safe_load((ROOT / "infra/docker/docker-compose.app.yml").read_text())
    assert api["services"]["helix-api"]["image"] == "helix-prime-api:${HELIX_API_IMAGE_TAG:-local}"
    assert (
        app["services"]["helix-app"]["image"]
        == "helix-prime-codex-app:${HELIX_APP_IMAGE_TAG:-local}"
    )


def test_app_image_exposes_source_packages_to_console_entrypoint() -> None:
    dockerfile = (ROOT / "infra/docker/Dockerfile.app").read_text()
    assert "PYTHONPATH=/app" in dockerfile
