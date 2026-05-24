#!/usr/bin/env bash
# CI full check — nightly / pre-release
# Requires LLM_API_KEY in environment. Exit 0 = all clear including live eval gates.
set -e

echo "=== CI Release Check ==="
echo ""

echo "[1/3] Security scan..."
python scripts/check_sensitive_files.py
echo "  OK"

echo "[2/3] Full live eval..."
python scripts/eval_grading.py --live --verbose
echo "  OK"

echo "[3/3] Unit tests..."
python -m pytest tests/ -q
echo "  OK"

echo ""
echo "=== All release checks passed ==="
