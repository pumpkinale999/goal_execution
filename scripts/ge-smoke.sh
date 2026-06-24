#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GE_URL="${GOAL_EXECUTION_URL:-http://127.0.0.1:8092}"
SK_URL="${SKSTUDIO_URL:-http://127.0.0.1:8000}"

echo "== ge-smoke: goal_execution health =="
curl -fsS "${GE_URL}/api/v1/health" | grep -q '"ok":true'

echo "== ge-smoke: skstudio health =="
curl -fsS "${SK_URL}/api/v1/health" 2>/dev/null | grep -q '"ok"' || curl -fsS "${SK_URL}/docs" >/dev/null

echo "== ge-smoke: org departments requires auth =="
code="$(curl -s -o /dev/null -w '%{http_code}' "${GE_URL}/api/v1/ge/objectives")"
test "$code" = "401" || test "$code" = "403"

echo "ge-smoke OK"
