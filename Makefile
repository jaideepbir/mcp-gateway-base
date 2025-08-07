SHELL := /bin/sh

OPA_POLICIES_DIR := services/opa/policies
OPA_TESTS_DIR := tests/policies

.PHONY: help policy-test opa-up opa-down opa-logs

help:
	@echo "Targets:"
	@echo "  policy-test   Run 'opa test' over $(OPA_POLICIES_DIR) and $(OPA_TESTS_DIR)"
	@echo "  opa-up        Start OPA in dev with decision logs enabled"
	@echo "  opa-down      Stop OPA dev container"
	@echo "  opa-logs      Tail OPA container logs"

policy-test:
	@echo "Running OPA unit tests..."
	@opa test $(OPA_POLICIES_DIR) $(OPA_TESTS_DIR) -v

opa-up:
	@echo "Starting OPA dev container with decision logs..."
	@cd compose && docker compose up -d opa

opa-down:
	@cd compose && docker compose down

opa-logs:
	@cd compose && docker compose logs -f opa
