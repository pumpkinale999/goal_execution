#!/usr/bin/env bash
# 运维 devops 工作副本 → rsync /opt/goal_execution → ge-deploy deploy
#
# 用法:
#   sudo /opt/goal_execution/deploy/ubuntu/ge-publish.sh
#
# 环境变量:
#   GE_SRC      默认 /home/devops/goal_execution
#   APP_ROOT    默认 /opt/goal_execution
set -euo pipefail

die() { echo "[ge-publish] 错误: $*" >&2; exit 1; }
log() { echo "[ge-publish] $*"; }

SRC="${GE_SRC:-/home/devops/goal_execution}"
APP_ROOT="${APP_ROOT:-/opt/goal_execution}"
readonly _GIT_USER="${GE_GIT_USER:-devops}"

[[ -d "${SRC}/.git" ]] || die "不是 git 仓库: ${SRC}（设置 GE_SRC）"

log "SRC=${SRC} -> APP_ROOT=${APP_ROOT}"

_git_pull_if_branch() {
  if [[ "${GE_SKIP_GIT_PULL:-0}" == "1" ]]; then
    log "GE_SKIP_GIT_PULL=1，跳过 git pull"
    return 0
  fi
  local branch
  branch="$(git symbolic-ref -q --short HEAD || true)"
  if [[ -n "$branch" ]]; then
    git pull
  else
    log "detached HEAD，跳过 git pull（已 checkout tag/commit）"
  fi
}

if [[ "$(id -u)" -eq 0 ]]; then
  log "git pull（用户 ${_GIT_USER}）"
  sudo -u "${_GIT_USER}" bash -c "set -euo pipefail; cd $(printf '%q' "$SRC"); $(declare -f _git_pull_if_branch); _git_pull_if_branch"
else
  log "git pull（当前用户）"
  ( cd "$SRC" && _git_pull_if_branch )
fi

log "rsync -> ${APP_ROOT}/"
sudo rsync -a --delete \
  --exclude=.git/ \
  --exclude=.venv/ \
  --exclude=data/ \
  --exclude=.pytest_cache/ \
  "${SRC}/" "${APP_ROOT}/"

log "chown ge:ge ${APP_ROOT}"
sudo chown -R ge:ge "$APP_ROOT"

DEPLOY="${APP_ROOT}/deploy/ubuntu/ge-deploy.sh"
[[ -f "$DEPLOY" ]] || die "未找到 ${DEPLOY}"

log "ge-deploy deploy"
sudo env APP_ROOT="$APP_ROOT" "$DEPLOY" deploy

log "完成。"
