#!/usr/bin/env bash
# 本地启动 goal_execution API（:8092 · ~/.hermes/goal-execution/）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DEFAULT_PORT=8092
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

CHECK_ONLY=0
NO_RUN=0
INSTALL_DEPS=0
AUTO_YES=1
SELECTED_PYTHON=""

log() { echo "[dev-goal-execution] $*"; }
die() { echo "[dev-goal-execution] 错误: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
用法: scripts/dev-goal-execution.sh [选项]

  默认：创建/激活 .venv · 复制 .env · 启动 uvicorn --reload :8092

  --check-only     只检查环境
  --install-deps   强制 pip install -e ".[dev]"
  --no-run         准备环境后不启动 HTTP
  --port PORT      监听端口（默认 8092）
  -h, --help       帮助

环境变量:
  SKSTUDIO_BACKEND  同步 JWT_SECRET / GOAL_EXECUTION_SERVICE_TOKEN（默认 ../skstudio/backend）
  HERMES_SHARED_ROOT  默认 $HOME/.hermes
EOF
}

pick_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN 不可用: $PYTHON_BIN"
    echo "$(command -v "$PYTHON_BIN")"
    return
  fi
  for c in python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 \
      && "$c" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)" 2>/dev/null; then
      echo "$(command -v "$c")"
      return
    fi
  done
  die "需要 Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
}

read_env_value() {
  local file=$1 key=$2
  [[ -f "$file" ]] || return 1
  grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true
}

patch_env_key() {
  local file=$1 key=$2 value=$3
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    local tmp
    tmp="$(mktemp)"
    awk -v k="$key" -v v="$value" '$1 == k { print k "=" v; next } { print }' FS='=' "$file" >"$tmp"
    mv "$tmp" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

sync_from_skstudio() {
  local sk_backend="${SKSTUDIO_BACKEND:-$REPO_ROOT/../skstudio/backend}"
  local src jwt token
  src="$sk_backend/.env"
  [[ -f "$src" ]] || return 0
  jwt="$(read_env_value "$src" JWT_SECRET)"
  token="$(read_env_value "$src" GOAL_EXECUTION_SERVICE_TOKEN)"
  if [[ -n "$jwt" ]]; then
    patch_env_key "$REPO_ROOT/.env" GOAL_EXECUTION_JWT_SECRET "$jwt"
    log "已从 skstudio 同步 GOAL_EXECUTION_JWT_SECRET"
  fi
  if [[ -n "$token" ]]; then
    patch_env_key "$REPO_ROOT/.env" GOAL_EXECUTION_SERVICE_TOKEN "$token"
    log "已从 skstudio 同步 GOAL_EXECUTION_SERVICE_TOKEN"
  fi
}

ensure_dotenv() {
  local envf="$REPO_ROOT/.env"
  local hermes_root="${HERMES_SHARED_ROOT:-$HOME/.hermes}"
  if [[ ! -f "$envf" ]]; then
    cp "$REPO_ROOT/.env.example" "$envf"
    log "已复制 .env"
  fi
  patch_env_key "$envf" GOAL_EXECUTION_DB_PATH "$hermes_root/goal-execution/data/ge.db"
  patch_env_key "$envf" SKSTUDIO_INTERNAL_URL "http://127.0.0.1:8000"
  sync_from_skstudio
}

ensure_venv() {
  SELECTED_PYTHON="$(pick_python_bin)"
  if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
    [[ "${CHECK_ONLY}" == 1 ]] && return 0
    "$SELECTED_PYTHON" -m venv "$REPO_ROOT/.venv"
    log "已创建 .venv"
  fi
}

activate_venv() {
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.venv/bin/activate"
}

ensure_pip_deps() {
  [[ "${CHECK_ONLY}" == 1 ]] && return 0
  if python -c "import fastapi, uvicorn" 2>/dev/null && [[ "${INSTALL_DEPS}" != 1 ]]; then
    return 0
  fi
  python -m pip install --upgrade pip setuptools wheel
  (cd "$REPO_ROOT" && pip install -e ".[dev]" --prefer-binary)
}

run_uvicorn() {
  [[ "${CHECK_ONLY}" == 1 || "${NO_RUN}" == 1 ]] && return 0
  log "启动 API: http://${HOST:-127.0.0.1}:${PORT}/api/v1/health"
  cd "$REPO_ROOT"
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
  exec uvicorn app.main:app --reload \
    --reload-exclude 'data/*' \
    --host "${HOST:-127.0.0.1}" --port "$PORT"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check-only) CHECK_ONLY=1 ;;
      --install-deps) INSTALL_DEPS=1 ;;
      --no-run) NO_RUN=1 ;;
      --port) PORT="${2:?}"; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "未知参数: $1" ;;
    esac
    shift
  done
  PORT="${PORT:-$DEFAULT_PORT}"
}

main() {
  parse_args "$@"
  cd "$REPO_ROOT"
  [[ -f pyproject.toml ]] || die "未找到 pyproject.toml"
  ensure_venv
  [[ "${CHECK_ONLY}" == 1 ]] && log "检查 OK（去掉 --check-only 以启动）" && exit 0
  activate_venv
  ensure_pip_deps
  ensure_dotenv
  run_uvicorn
}

main "$@"
