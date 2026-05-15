# ProxmoxPubliseradeWebbLoggar

Ett enkelt Python/Flask-projekt som publicerar textloggar (`.txt`) via webbläsare.

## Funktioner

- Listar alla `.txt`-filer i `logs/`
- Visar varje loggfil som ren text via `/logs/<filnamn>`
- Enkel startsida på `/`

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

Lägg dina loggfiler som `.txt` i `logs/`.

## Deployment i Proxmox LXC (Debian/Ubuntu)

1. Skapa en LXC-container i Proxmox (t.ex. Debian 12).
2. SSH in i containern och installera paket:
   - `apt update`
   - `apt install -y python3 python3-venv python3-pip git`
3. Klona ditt repo:
   - `git clone <DIN_GITHUB_REPO_URL> /opt/logweb`
   - `cd /opt/logweb`
4. Skapa och aktivera virtuell miljö:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
5. Installera beroenden:
   - `pip install -r requirements.txt`
6. Testa körning med gunicorn:
   - `gunicorn -b 0.0.0.0:8080 app:app`

### Systemd service (valfritt men rekommenderat)

Skapa filen `/etc/systemd/system/logweb.service`:

```ini
[Unit]
Description=Loggwebb Flask Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/logweb
Environment="PATH=/opt/logweb/.venv/bin"
ExecStart=/opt/logweb/.venv/bin/gunicorn -b 0.0.0.0:8080 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Aktivera tjänsten:

- `systemctl daemon-reload`
- `systemctl enable --now logweb`
- `systemctl status logweb`

### Nginx reverse proxy (port 80/443)

1. Installera Nginx:
   - `apt install -y nginx`
2. Kopiera konfigurationen från projektet:
   - `cp /opt/logweb/deploy/nginx-logweb.conf /etc/nginx/sites-available/logweb`
3. Aktivera site och verifiera syntax:
   - `ln -s /etc/nginx/sites-available/logweb /etc/nginx/sites-enabled/logweb`
   - `nginx -t`
4. Starta om Nginx:
   - `systemctl restart nginx`

För HTTPS med LetsEncrypt, ersatt `your-domain` i konfigfilen och skapa certifikat innan du laddar om Nginx.

Exempel med certbot (om DNS pekar mot containern):

- `apt install -y certbot python3-certbot-nginx`
- `certbot --nginx -d ditt-domannamn`
- `systemctl reload nginx`

## GitHub snabbstart

1. Initiera git lokalt:
   - `git init`
   - `git add .`
   - `git commit -m "Initial commit: log web server for Proxmox LXC"`
2. Skapa tomt repo på GitHub och koppla remote:
   - `git remote add origin <DIN_GITHUB_REPO_URL>`
3. Pusha:
   - `git branch -M main`
   - `git push -u origin main`
