#!/usr/bin/env bash
set -euo pipefail

CREDENTIALS_FILE="/etc/letsencrypt/duckdns/credentials.ini"
PROPAGATION_SECONDS="${DNS_PROPAGATION_SECONDS:-60}"
EMAIL="${1:-}"

MAIN_CERT_NAME="rud4berg.duckdns.org"
MAIN_DOMAINS=(
  "rud4berg.duckdns.org"
  "rud4bergimmich.duckdns.org"
)

LOG_CERT_NAME="rudbergloggar.duckdns.org"
LOG_DOMAINS=(
  "rudbergloggar.duckdns.org"
)

if [ "$(id -u)" -ne 0 ]; then
  echo "Error: run as root (needed for certbot and systemctl)." >&2
  exit 1
fi

if [ -z "$EMAIL" ]; then
  echo "Usage: $0 <email>" >&2
  echo "Example: $0 admin@example.com" >&2
  exit 1
fi

if [ ! -f "$CREDENTIALS_FILE" ]; then
  echo "Error: missing DuckDNS credentials file: $CREDENTIALS_FILE" >&2
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo "Error: certbot is not installed." >&2
  exit 1
fi

echo "==> Requesting/updating certificate: $MAIN_CERT_NAME"
for domain in "${MAIN_DOMAINS[@]}"; do
  echo " - $domain"
done

certbot certonly \
  --authenticator dns-duckdns \
  --dns-duckdns-credentials "$CREDENTIALS_FILE" \
  --dns-duckdns-propagation-seconds "$PROPAGATION_SECONDS" \
  --cert-name "$MAIN_CERT_NAME" \
  --expand \
  -d "${MAIN_DOMAINS[0]}" \
  -d "${MAIN_DOMAINS[1]}" \
  -m "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --non-interactive

echo "==> Requesting/updating certificate: $LOG_CERT_NAME"
for domain in "${LOG_DOMAINS[@]}"; do
  echo " - $domain"
done

certbot certonly \
  --authenticator dns-duckdns \
  --dns-duckdns-credentials "$CREDENTIALS_FILE" \
  --dns-duckdns-propagation-seconds "$PROPAGATION_SECONDS" \
  --cert-name "$LOG_CERT_NAME" \
  -d "${LOG_DOMAINS[0]}" \
  -m "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --non-interactive

echo "==> Installed certificates"
certbot certificates

echo "==> Validating and reloading nginx"
nginx -t
systemctl reload nginx

echo "Certificate update complete."
