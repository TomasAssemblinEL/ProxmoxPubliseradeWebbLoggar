#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/logweb"
BRANCH="${1:-main}"
NGINX_SOURCE="$APP_DIR/deploy/nginx-logweb.conf"
NGINX_TARGET="/etc/nginx/sites-available/reverse-proxy"

if [ "$(id -u)" -ne 0 ]; then
  echo "Error: run as root (needed for systemctl)." >&2
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Error: $APP_DIR is not a git repository." >&2
  exit 1
fi

cd "$APP_DIR"

echo "==> Checking local git status"
if [ -n "$(git status --porcelain)" ]; then
  echo "Error: local changes detected in $APP_DIR." >&2
  echo "Commit/stash changes first, then run again." >&2
  exit 1
fi

echo "==> Pulling latest from origin/$BRANCH"
git fetch origin "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "==> Installing/updating Python dependencies"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Installing Nginx config"
install -m 644 "$NGINX_SOURCE" "$NGINX_TARGET"

echo "==> Restarting services"
systemctl restart logweb
nginx -t
systemctl reload nginx

echo "==> Service status"
systemctl is-active --quiet logweb && echo "logweb: active"
systemctl is-active --quiet nginx && echo "nginx: active"

echo "==> Local health check"
if command -v curl >/dev/null 2>&1; then
  HEALTH_OK=0
  for i in $(seq 1 20); do
    if curl -fsS -o /dev/null http://127.0.0.1:8080/; then
      HEALTH_OK=1
      echo "app: ok (attempt $i/20)"
      break
    fi
    sleep 1
  done

  if [ "$HEALTH_OK" -ne 1 ]; then
    echo "Warning: app health-check failed after 20 seconds." >&2
    echo "Check: systemctl status logweb --no-pager -l" >&2
    echo "Check: journalctl -u logweb -n 80 --no-pager" >&2
  fi
else
  echo "curl not found, skipped health check"
fi

echo "Update complete."
