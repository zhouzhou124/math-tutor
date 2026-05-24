#!/usr/bin/env bash
# CI fast check — PR / local pre-commit
# Runs without LLM keys. Exit 0 = all clear.
set -e

echo "=== CI Fast Check ==="
echo ""

echo "[1/3] Security scan..."
python scripts/check_sensitive_files.py
echo "  OK"

echo "[2/3] Eval dataset dry-run..."
python scripts/eval_grading.py
echo "  OK"

echo "[3/3] Unit tests..."
python -m pytest tests/ -q
echo "  OK"

echo ""
echo "=== All checks passed ==="
