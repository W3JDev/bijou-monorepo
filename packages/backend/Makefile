# Bijou AI Enterprise - Developer Makefile
# ============================================================
# First time on this repo?  ->  make setup      (fast, ~30 seconds)
# Before every push?        ->  make test       (auto-runs via pre-push hook)
# Full CI simulation?       ->  make ci-check
# Deploy production?        ->  make deploy-production
# ============================================================
# NOTE: `make setup` uses requirements-dev.txt (no torch/CUDA).
# Docker/Fly.io uses requirements.txt (full, including torch/TTS).
# ============================================================

.PHONY: help setup audit audit-strict audit-json lint test test-fast check-root clean ci-check

help:
	@echo ""
	@echo "  Bijou AI Developer Commands"
	@echo "  ----------------------------"
	@echo "  make setup         Install DEV deps + pre-commit hooks (ONCE per clone, ~30s)"
	@echo "  make audit         Run 14-check static auditor (same as CI gate)"
	@echo "  make audit-strict  Audit in strict mode (P2 also blocks)"
	@echo "  make lint          Run pre-commit on all files"
	@echo "  make test          Run pytest (auto-runs before every push)"
	@echo "  make check-root    Check root folder cleanliness only"
	@echo "  make clean         Remove __pycache__, .pyc, temp files"
	@echo "  make ci-check      Simulate full CI: audit + tests (run before PR)"
	@echo ""
	@echo "  NOTE: setup uses requirements-dev.txt (no torch/CUDA/ML packages)"
	@echo "  Production deps (torch etc) are only installed by Docker/Fly.io"
	@echo ""

# --- SETUP (run once per developer per clone, ~30 seconds) ---
# Uses requirements-dev.txt NOT requirements.txt.
# requirements.txt is for production Docker/Fly.io builds only.
setup:
	@echo "-> Installing dev dependencies (no torch/CUDA — fast)..."
	pip install -r requirements-dev.txt
	@echo "-> Installing commit hook (audit runs on every commit)..."
	pre-commit install
	@echo "-> Installing push hook (tests run on every push)..."
	pre-commit install --hook-type pre-push
	@echo "-> Installing commit-msg hook..."
	pre-commit install --hook-type commit-msg
	@echo ""
	@echo "Setup complete. Three automatic gates now active:"
	@echo "  git commit  -> static audit (14 checks, blocks P0/P1)"
	@echo "  git push    -> pytest (blocks if any test fails)"
	@echo "  GitHub PR   -> CI audit + test job (cannot merge if red)"
	@echo ""

# --- AUDIT (same 14 checks as CI) ---
audit:
	@echo "-> Running Bijou Static Auditor..."
	python scripts/static_audit.py

audit-strict:
	@echo "-> Running Bijou Static Auditor (STRICT - P2 also fails)..."
	python scripts/static_audit.py --strict

audit-json:
	python scripts/static_audit.py --json

# --- LINT (pre-commit on all files) ---
lint:
	@echo "-> Running pre-commit on all files..."
	pre-commit run --all-files

# --- TEST ---
# This also runs automatically before every `git push` (pre-push hook)
# If a push is blocked: fix the failing test, then push again
test:
	@echo "-> Running pytest..."
	pytest tests/ -v --tb=short

test-fast:
	@echo "-> Running pytest (fail on first error, no slow tests)..."
	pytest tests/ -x -q --tb=short -m "not slow"

# --- CHECK ROOT ---
check-root:
	@echo "-> Checking root folder cleanliness..."
	python scripts/static_audit.py 2>&1 | grep -A2 "RootClutter\|FILE_IN_ROOT" || echo "Root is clean."

# --- CLEAN ---
clean:
	@echo "-> Cleaning temp files..."
	find . -type d -name __pycache__ -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true
	find . -name "bandit_report.json" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "Clean."

# --- CI GATE (full simulation of what GitHub CI does) ---
# Run this before opening a PR to guarantee it will pass
ci-check:
	@echo "-> [CI GATE] Step 1/2: Static Audit..."
	python scripts/static_audit.py --strict
	@echo "-> [CI GATE] Step 2/2: Pytest..."
	pytest tests/ -v --tb=short
	@echo ""
	@echo "CI gate passed. Safe to open a PR."
