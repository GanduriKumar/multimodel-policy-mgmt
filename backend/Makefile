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
    tests/test_api_protect.py \
    tests/test_api_evidence.py \
    tests/test_api_policies.py \
    tests/test_api_audit.py

.PHONY: help test test-unit test-integration test-api lint format run

help:
    @echo "Available targets:"
    @echo "  test               Run all tests"
    @echo "  test-unit          Run unit tests"
    @echo "  test-integration   Run integration tests"
    @echo "  test-api           Run API tests"
    @echo "  lint               Run Ruff checks (lint and format check)"
    @echo "  format             Apply Ruff formatting"
    @echo "  run                Start FastAPI with uvicorn --reload"

test:
    $(PYTHON) -m $(PYTEST) -q

test-unit:
    $(PYTHON) -m $(PYTEST) -q $(UNIT_FILES)

test-integration:
    $(PYTHON) -m $(PYTEST) -q $(INTEGRATION_FILES)

test-api:
    $(PYTHON) -m $(PYTEST) -q $(API_FILES)

lint:
    $(PYTHON) -m $(RUFF) check app tests
    $(PYTHON) -m $(RUFF) format --check app tests

format:
    $(PYTHON) -m $(RUFF) format app tests

run:
    $(PYTHON) -m $(UVICORN) app.main:app --reload --port 8000