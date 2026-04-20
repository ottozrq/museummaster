#!/usr/bin/env bash
# 供服务器 crontab 定时调用：拉取最新代码、生成新闻页与 sitemap，可选同步到站点目录。
#
# 用法（在仓库根目录）：
#   ./website/scripts/cron-build-website.sh
#
# 环境变量（均为可选）：
#   GIT_PULL=1              执行前先 git pull --ff-only（需在仓库内、已配置 remote）
#   WEBSITE_DEPLOY_RSYNC_TARGET=user@host:/var/www/cacaou/
#                           若设置，构建成功后 rsync 整个 website/ 到该目标（末尾建议带 /）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

if [[ "${GIT_PULL:-0}" == "1" ]]; then
  git pull --ff-only
fi

node website/scripts/build-news.mjs

if [[ -n "${WEBSITE_DEPLOY_RSYNC_TARGET:-}" ]]; then
  rsync -av --delete "${REPO_ROOT}/website/" "${WEBSITE_DEPLOY_RSYNC_TARGET}"
fi
