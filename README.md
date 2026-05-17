# ProxmoxPubliseradeWebbLoggar

Ett Python/Flask-projekt som publicerar textloggar (`.txt`) via webbläsare.

## Funktioner

- Listar `.txt`-filer grupperade i kategorier: `VMM1`, `VMM2`, `MixTank`, `Irrigation`
- Visar varje loggfil som ren text via `/logs/<kategori>/<filnamn>`
- Enkel startsida på `/`
- Fungerar bakom Nginx reverse proxy med HTTPS

## Lokal körning

1. Skapa virtuell miljö:
   - `python -m venv .venv`
2. Aktivera miljön:
   - PowerShell: `.\.venv\Scripts\Activate.ps1`
3. Installera beroenden:
   - `pip install -r requirements.txt`
4. Starta appen:
   - `python app.py`
5. Öppna:
   - `http://localhost:8080`

Lägg dina loggfiler som `.txt` i respektive kategori:

- `logs/VMM1/`
- `logs/VMM2/`
- `logs/MixTank/`
- `logs/Irrigation/`

## Produktion (nuvarande upplägg)

- Proxmox loggserver: `192.168.1.65`
- Home Assistant: `192.168.1.166`
- Loggdomän: `rudbergloggar.duckdns.org`
- HA-domän: `rud4berg.duckdns.org`
- Publik port forward i UniFi:
  - TCP 80 -> `192.168.1.65:80`
  - TCP 443 -> `192.168.1.65:443`

## Deployment i Proxmox LXC (Debian/Ubuntu)

1. Installera paket:
   - `apt update`
   - `apt install -y python3 python3-venv python3-pip git nginx`
2. Klona repo:
   - `git clone <DIN_GITHUB_REPO_URL> /opt/logweb`
   - `cd /opt/logweb`
3. Skapa virtuell miljö och installera beroenden:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`

### Systemd service

Skapa `/etc/systemd/system/logweb.service`:

```ini
[Unit]
Description=Loggwebb Flask Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/logweb
Environment="PATH=/opt/logweb/.venv/bin"
ExecStart=/opt/logweb/.venv/bin/gunicorn -b 127.0.0.1:8080 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Aktivera:

- `systemctl daemon-reload`
- `systemctl enable --now logweb`
- `systemctl status logweb`

### Nginx (dual-domain reverse proxy)

Kopiera projektets konfig:

- `cp /opt/logweb/deploy/nginx-logweb.conf /etc/nginx/sites-available/reverse-proxy`
- `rm -f /etc/nginx/sites-enabled/default`
- `ln -sfn /etc/nginx/sites-available/reverse-proxy /etc/nginx/sites-enabled/reverse-proxy`
- `nginx -t`
- `systemctl enable --now nginx`
- `systemctl reload nginx`

## HTTPS med Let's Encrypt + DuckDNS (DNS-01)

Använd DNS-challenge om HTTP-challenge störs av redirect/annan ingress.

1. Installera plugin:
   - `apt install -y python3-certbot-dns-duckdns`
2. Skapa credentials-fil (OBS: håll token hemligt):

```bash
mkdir -p /etc/letsencrypt/duckdns
cat > /etc/letsencrypt/duckdns/credentials.ini <<'EOF'
dns_duckdns_token = DITT_DUCKDNS_TOKEN
EOF
chmod 600 /etc/letsencrypt/duckdns/credentials.ini
```

3. Hämta certifikat:

```bash
certbot certonly \
  --authenticator dns-duckdns \
  --dns-duckdns-credentials /etc/letsencrypt/duckdns/credentials.ini \
  --dns-duckdns-propagation-seconds 60 \
  -d rud4berg.duckdns.org \
  -d rudbergloggar.duckdns.org \
  -m dinmail@exempel.se \
  --agree-tos --no-eff-email --non-interactive
```

4. Ladda om Nginx:
   - `nginx -t && systemctl reload nginx`

## Delad loggmapp mellan Node-RED och loggserver (unprivileged LXC)

Mål: Node-RED skriver i delad mapp och loggwebben publicerar samma filer.

### 1) På Proxmox host

```bash
# Exempel-CTID, byt vid behov
CT_NODE=101
CT_LOG=102

mkdir -p /srv/shared/nodered-logs

# Standard unprivileged mapping: container 1500 -> host 101500
chown 101500:101500 /srv/shared/nodered-logs
chmod 2770 /srv/shared/nodered-logs

pct set $CT_NODE -mp0 /srv/shared/nodered-logs,mp=/opt/nodered-logs
pct set $CT_LOG  -mp0 /srv/shared/nodered-logs,mp=/opt/logweb/logs

pct stop $CT_NODE; pct start $CT_NODE
pct stop $CT_LOG;  pct start $CT_LOG
```

### 2) I Node-RED-container

```bash
groupadd -g 1500 sharedlogs || true
usermod -aG sharedlogs nodered
echo "test $(date)" > /opt/nodered-logs/test.txt
```

### 3) I loggserver-container

```bash
groupadd -g 1500 sharedlogs || true
usermod -aG sharedlogs www-data
cat /opt/logweb/logs/test.txt
```

## Node-RED skrivmönster (exempel)

Skriv till:

- `/opt/nodered-logs/VMM1/log-YYYY-MM-DD.txt`
- `/opt/nodered-logs/VMM2/log-YYYY-MM-DD.txt`
- `/opt/nodered-logs/MixTank/log-YYYY-MM-DD.txt`
- `/opt/nodered-logs/Irrigation/log-YYYY-MM-DD.txt`

och appenda en rad i taget, t.ex.:

- `2026-05-17 12:00:00 INFO heartbeat ok`

## GitHub snabbstart

1. Initiera git lokalt:
   - `git init`
   - `git add .`
   - `git commit -m "Initial commit: log web server for Proxmox LXC"`
2. Koppla remote:
   - `git remote add origin <DIN_GITHUB_REPO_URL>`
3. Pusha:
   - `git branch -M main`
   - `git push -u origin main`
