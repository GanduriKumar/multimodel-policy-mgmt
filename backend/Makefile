SHELL := /usr/bin/env bash
PYTHON ?= python
PYTEST ?= pytest
UVICORN ?= uvicorn
RUFF ?= ruff

# Group tests by intent. Adjust lists if new tests are added.
UNIT_FILES := \
	tests/test_hashing.py \
	tests/test_patterns.py \
	tests/test_risk_engine.py \
	tests/test_policy_engine.py \
	tests/test_auth.py \
	tests/test_decision_service_unit.py \
	tests/test_auth_service_unit.py

INTEGRATION_FILES := \
	tests/test_policy_repo.py \
	tests/test_evidence_repo.py \
	tests/test_audit_repo.py \
	tests/test_tenant_repo.py

API_FILES := \
	tests/test_api_protect.py

.PHONY: help test-unit test-integration test-api lint run

help:
	@echo "Available targets:"
	@echo "  test-unit         Run unit tests"
	@echo "  test-integration  Run integration tests"
	@echo "  test-api          Run API tests"
	@echo "  lint              Run Ruff checks (lint and format check)"
	@echo "  run               Start FastAPI with uvicorn --reload"

test-unit:
	$(PYTHON) -m $(PYTEST) -q $(UNIT_FILES)

test-integration:
	$(PYTHON) -m $(PYTEST) -q $(INTEGRATION_FILES)

test-api:
	$(PYTHON) -m $(PYTEST) -q $(API_FILES)

lint:
	$(PYTHON) -m $(RUFF) check app tests
	$(PYTHON) -m $(RUFF) format --check app tests

run:
	$(PYTHON) -m $(UVICORN) app.main:app --reload --port 8000
