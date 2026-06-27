#!/usr/bin/env bash
# goal_execution Ubuntu 部署 — bootstrap + configure + deploy + health
set -euo pipefail

die() { echo "[ge-deploy] 错误: $*" >&2; exit 1; }
log() { echo "[ge-deploy] $*"; }

_script_realpath() {
  local p="${BASH_SOURCE[0]}"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$p"
  else
    readlink -f "$p" 2>/dev/null || echo "$p"
  fi
}

DEPLOY_DIR="$(cd "$(dirname "$(_script_realpath)")" && pwd)"
APP_ROOT="${APP_ROOT:-/opt/goal_execution}"
GE_USER="${GE_USER:-ge}"
GE_HOME="${GE_HOME:-/var/lib/ge}"
GE_PORT="${GE_PORT:-8092}"
HERMES_SHARED_ROOT="${HERMES_SHARED_ROOT:-/var/lib/hermes}"
SKSTUDIO_ENV="${SKSTUDIO_ENV:-/etc/skstudio/skstudio.env}"
GE_ENV="/etc/goal-execution/goal-execution.env"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"; }

ensure_sudo() {
  [[ "$(id -u)" -eq 0 ]] && return 0
  sudo -v || die "需要 sudo 权限"
}

resolve_python_bin() {
  local candidate ver major minor
  for candidate in python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if (( major > MIN_PYTHON_MAJOR || (major == MIN_PYTHON_MAJOR && minor >= MIN_PYTHON_MINOR) )); then
      printf '%s' "$candidate"
      return 0
    fi
  done
  die "未找到 Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
}

render_service_unit() {
  local src="$DEPLOY_DIR/goal-execution.service.in"
  local out="$1"
  [[ -f "$src" ]] || die "缺少 $src"
  sed -e "s|__APP_ROOT__|${APP_ROOT}|g" \
    -e "s|__PORT__|${GE_PORT}|g" \
    "$src" >"$out"
}

read_env_value() {
  local file=$1 key=$2
  [[ -f "$file" ]] || return 1
  grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true
}

is_placeholder_token() {
  local value="${1:-}"
  [[ -z "$value" ]] && return 0
  [[ "$value" == *"替换"* ]] && return 0
  [[ "$value" == *"change-me"* ]] && return 0
  ! printf '%s' "$value" | LC_ALL=C grep -q '^[A-Za-z0-9._-]\+$'
}

set_env_key() {
  local file=$1 key=$2 value=$3
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$file" ]]; then
    grep -vE "^${key}=" "$file" >"$tmp" || true
  else
    : >"$tmp"
  fi
  printf '%s=%s\n' "$key" "$value" >>"$tmp"
  mv "$tmp" "$file"
}

check_env_file() {
  ensure_sudo
  sudo test -f "$GE_ENV" || die "缺少 $GE_ENV（先 bootstrap 或 configure）"
  if sudo grep -qE '^GOAL_EXECUTION_JWT_SECRET=(替换|change-me)\s*$' "$GE_ENV" 2>/dev/null; then
    die "请在 $GE_ENV 设置 GOAL_EXECUTION_JWT_SECRET（与 skstudio JWT_SECRET 同值）"
  fi
  local token_line
  token_line="$(sudo grep -E '^GOAL_EXECUTION_SERVICE_TOKEN=' "$GE_ENV" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  if is_placeholder_token "$token_line"; then
    die "请在 $GE_ENV 设置 ASCII GOAL_EXECUTION_SERVICE_TOKEN（运行 ge-deploy configure）"
  fi
}

preflight() {
  log "Preflight"
  need_cmd curl
  command -v systemctl >/dev/null 2>&1 || die "缺少 systemctl"
  resolve_python_bin >/dev/null
  id "$GE_USER" >/dev/null 2>&1 || die "系统用户 ${GE_USER} 不存在（先 bootstrap）"
  [[ -d "$APP_ROOT/app" ]] || die "未找到 app/（APP_ROOT=$APP_ROOT）"
  log "Preflight OK"
}

bootstrap() {
  ensure_sudo
  log "Bootstrap — 用户 ${GE_USER}、目录、systemd、env 模板"
  if ! id "$GE_USER" >/dev/null 2>&1; then
    sudo useradd --system --home "$GE_HOME" --shell /usr/sbin/nologin "$GE_USER" \
      || sudo useradd --system --home "$GE_HOME" --shell /bin/false "$GE_USER"
  fi
  sudo mkdir -p "$GE_HOME" "$APP_ROOT" "${GE_HOME}/goal-execution/data"
  sudo chown -R "${GE_USER}:${GE_USER}" "$GE_HOME"
  sudo mkdir -p /etc/goal-execution
  if [[ ! -f /etc/goal-execution/goal-execution.env ]]; then
    sudo install -m 0600 -o root -g root \
      "$DEPLOY_DIR/goal-execution.env.example" "$GE_ENV"
    log "已创建 $GE_ENV — 请 configure 或手工编辑密钥后再 deploy"
  fi
  local tmp
  tmp="$(mktemp)"
  render_service_unit "$tmp"
  sudo install -m 0644 "$tmp" /etc/systemd/system/goal-execution.service
  rm -f "$tmp"
  sudo systemctl daemon-reload
  log "Bootstrap 完成"
}

configure() {
  ensure_sudo
  sudo test -f "$SKSTUDIO_ENV" || die "缺少 $SKSTUDIO_ENV"
  [[ -f "$GE_ENV" ]] || bootstrap
  local jwt sk_token ge_token
  jwt="$(read_env_value "$SKSTUDIO_ENV" JWT_SECRET)"
  [[ -n "$jwt" ]] || die "无法从 $SKSTUDIO_ENV 读取 JWT_SECRET"

  sk_token="$(read_env_value "$SKSTUDIO_ENV" GOAL_EXECUTION_SERVICE_TOKEN)"
  ge_token="$(read_env_value "$GE_ENV" GOAL_EXECUTION_SERVICE_TOKEN)"
  if is_placeholder_token "$sk_token"; then sk_token=""; fi
  if is_placeholder_token "$ge_token"; then ge_token=""; fi
  if [[ -z "$sk_token" && -z "$ge_token" ]]; then
    sk_token="$(openssl rand -hex 24)"
    ge_token="$sk_token"
    log "已生成 GOAL_EXECUTION_SERVICE_TOKEN"
  elif [[ -n "$sk_token" ]]; then
    ge_token="$sk_token"
  elif [[ -n "$ge_token" ]]; then
    sk_token="$ge_token"
  fi

  sudo cp "$GE_ENV" "${GE_ENV}.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  set_env_key "$GE_ENV" GOAL_EXECUTION_JWT_SECRET "$jwt"
  set_env_key "$GE_ENV" GOAL_EXECUTION_SERVICE_TOKEN "$ge_token"
  set_env_key "$GE_ENV" GOAL_EXECUTION_DB_PATH "${GE_HOME}/goal-execution/data/ge.db"
  set_env_key "$GE_ENV" SKSTUDIO_INTERNAL_URL "http://127.0.0.1:8000"
  set_env_key "$GE_ENV" HOST "127.0.0.1"
  set_env_key "$GE_ENV" PORT "$GE_PORT"
  sudo chmod 600 "$GE_ENV"
  sudo chown root:root "$GE_ENV"

  sudo cp "$SKSTUDIO_ENV" "${SKSTUDIO_ENV}.bak.$(date +%Y%m%d%H%M%S)"
  set_env_key "$SKSTUDIO_ENV" GOAL_EXECUTION_URL "http://127.0.0.1:${GE_PORT}"
  set_env_key "$SKSTUDIO_ENV" GOAL_EXECUTION_SERVICE_TOKEN "$sk_token"
  sudo chmod 600 "$SKSTUDIO_ENV"

  log "已同步 JWT_SECRET / GOAL_EXECUTION_SERVICE_TOKEN（goal-execution ↔ skstudio）"
  log "configure 完成 — 下一步: ge-publish 或 ge-deploy deploy"
}

run_as_ge() {
  sudo -u "$GE_USER" env HOME="$GE_HOME" TMPDIR="${TMPDIR:-/tmp}" bash -lc "set -euo pipefail; cd \"$APP_ROOT\"; $*"
}

install_app() {
  log "安装 Python 依赖"
  local py_bin
  py_bin="$(resolve_python_bin)"
  ensure_sudo
  if [[ ! -x "$APP_ROOT/.venv/bin/python" ]]; then
    run_as_ge "$py_bin" -m venv .venv
  fi
  run_as_ge ".venv/bin/pip install --upgrade pip setuptools wheel"
  run_as_ge ".venv/bin/pip install -e '.[dev]' --prefer-binary"
}

migrate_db() {
  log "Database：alembic upgrade head（root source ${GE_ENV} 后 runuser -u ${GE_USER}）"
  ensure_sudo
  check_env_file
  sudo mkdir -p "${GE_HOME}/goal-execution/data"
  sudo chown -R "${GE_USER}:${GE_USER}" "${GE_HOME}/goal-execution" 2>/dev/null || true
  sudo bash -lc "
    set -euo pipefail
    command -v runuser >/dev/null 2>&1 || { echo '缺少 runuser（util-linux）' >&2; exit 1; }
    set -a
    source \"${GE_ENV}\"
    set +a
    cd \"${APP_ROOT}\"
    runuser -u ${GE_USER} -- env HOME=\"${GE_HOME}\" TMPDIR=/tmp ./.venv/bin/alembic upgrade head
  "
}

start_service() {
  ensure_sudo
  check_env_file
  sudo chown -R "${GE_USER}:${GE_USER}" "$APP_ROOT" 2>/dev/null || true
  sudo chown -R "${GE_USER}:${GE_USER}" "${GE_HOME}/goal-execution" 2>/dev/null || true
  sudo systemctl enable goal-execution.service
  sudo systemctl restart goal-execution.service
  sudo systemctl is-active --quiet goal-execution.service || {
    sudo journalctl -u goal-execution.service -n 40 --no-pager >&2 || true
    die "goal-execution.service 未 active"
  }
}

verify_health() {
  local url="http://127.0.0.1:${GE_PORT}/api/v1/health"
  log "健康检查: $url"
  local i out
  for i in $(seq 1 20); do
    if out="$(curl -sf "$url" 2>/dev/null)"; then
      echo "$out" | grep -q goal_execution || echo "$out" | grep -q '"ok"' || die "health 响应异常: $out"
      log "✓ health OK"
      return 0
    fi
    sleep 1
  done
  die "health 检查失败: $url"
}

print_checklist() {
  log "---------- skstudio 对照清单 ----------"
  log "skstudio.env 须含:"
  log "  GOAL_EXECUTION_URL=http://127.0.0.1:${GE_PORT}"
  log "  GOAL_EXECUTION_SERVICE_TOKEN=<与 $GE_ENV 同值>"
  log "Nginx /ge-api/ 须反代至 :${GE_PORT}（skstudio deploy sync-nginx）"
  log "重启: sudo systemctl restart skstudio goal-execution"
}

deploy() {
  preflight
  install_app
  migrate_db
  start_service
  verify_health
  print_checklist
  log "Deploy 完成"
}

usage() {
  cat <<EOF
用法: deploy/ubuntu/ge-deploy.sh <bootstrap|configure|deploy|health>

  bootstrap    创建 ge 用户、数据目录、systemd unit、env 模板
  configure    从 /etc/skstudio/skstudio.env 同步 JWT + service token
  deploy       pip install + alembic upgrade head + 启动 goal-execution.service + health
  health       仅 curl /api/v1/health

环境变量: APP_ROOT GE_PORT HERMES_SHARED_ROOT GE_USER SKSTUDIO_ENV
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    bootstrap) bootstrap ;;
    configure) configure ;;
    deploy) deploy ;;
    health) verify_health ;;
    -h|--help|help) usage ;;
    *) die "用法: $0 bootstrap|configure|deploy|health" ;;
  esac
}

if [[ "${GE_DEPLOY_TEST_MODE:-}" == 1 ]]; then
  :
elif [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
