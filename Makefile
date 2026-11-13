# Helix-Codex developer Makefile
#
# Convenience targets for running the mock server (parallel-development API)
# and, optionally, the real app beside it. No secrets, no network exposure:
# everything binds loopback via `network_mode: host` in the compose files.

DOCKER_DIR := infra/docker
MOCK_COMPOSE := $(DOCKER_DIR)/docker-compose.mock.yml
APP_COMPOSE := $(DOCKER_DIR)/docker-compose.app.yml
MOCK_TAG ?= local
SCENARIO ?= default

.PHONY: mock-build mock-up mock-down mock-logs mock-test mock-shell dev-up dev-down

# Build the mock image.
mock-build:
	docker compose -f $(MOCK_COMPOSE) build

# Start the mock server on http://127.0.0.1:8001 (scenario from $(SCENARIO)).
mock-up:
	MOCK_SCENARIO=$(SCENARIO) docker compose -f $(MOCK_COMPOSE) up -d --build

# Stop and remove the mock container.
mock-down:
	docker compose -f $(MOCK_COMPOSE) down

# Follow mock logs.
mock-logs:
	docker compose -f $(MOCK_COMPOSE) logs -f helix-mock

# Open a shell inside the running mock container.
mock-shell:
	docker compose -f $(MOCK_COMPOSE) exec helix-mock sh

# Run the mock contract test suite locally (no Docker needed).
mock-test:
	python3 -m pytest tests/mock_server/ -q

# Bring up BOTH the real app (8100) and the mock (8001) for side-by-side work.
dev-up:
	MOCK_SCENARIO=$(SCENARIO) docker compose -f $(APP_COMPOSE) -f $(MOCK_COMPOSE) up -d --build

# Tear down both.
dev-down:
	docker compose -f $(APP_COMPOSE) -f $(MOCK_COMPOSE) down
