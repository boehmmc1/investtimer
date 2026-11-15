#!/usr/bin/env bash
# Einmalige Einrichtung auf dem Server. Gefahrlos wiederholbar.
# Fasst nur investtimer-Dateien an (eigener nginx-Block, eigene Timer).
set -euo pipefail

REPO_DIR=/var/www/investtimer
DATA_DIR=/var/lib/investtimer/data
ENV_FILE=/etc/investtimer.env
KEY=/root/.ssh/investtimer_deploy

[ "$(id -u)" = 0 ] || { echo "Bitte als root ausfuehren."; exit 1; }
for tool in nginx python3 git; do
    command -v "$tool" >/dev/null || { echo "Fehlt: $tool"; exit 1; }
done

echo "== 1/5 Repo"
if [ -f "$KEY" ]; then
    git -C "$REPO_DIR" config core.sshCommand "ssh -i $KEY -o IdentitiesOnly=yes"
fi
chmod +x "$REPO_DIR"/deploy/*.sh "$REPO_DIR"/server/update_stress.py
mkdir -p "$DATA_DIR"

echo "== 2/5 Datenquelle ($ENV_FILE)"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" <<EOF
# InvestTimer holt nur das fertige Ergebnis von der Volafly-API.
STRESS_API_URL=https://api.volafly.net/v1/marktstress
OUTPUT_PATH=$DATA_DIR/stress.json
EOF
    echo "angelegt."
else
    echo "vorhanden, unveraendert."
fi

echo "== 3/5 Timer (Daten alle 10 min, Deploy alle 2 min, Zertifikat bis vorhanden)"
unit() { cat > "/etc/systemd/system/$1"; }
unit investtimer-data.service <<EOF
[Unit]
Description=InvestTimer: Marktstress berechnen
[Service]
Type=oneshot
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/python3 $REPO_DIR/server/update_stress.py
EOF
unit investtimer-data.timer <<EOF
[Unit]
Description=InvestTimer: Marktstress alle 10 Minuten
[Timer]
OnBootSec=1min
OnUnitActiveSec=10min
[Install]
WantedBy=timers.target
EOF
unit investtimer-deploy.service <<EOF
[Unit]
Description=InvestTimer: Stand von GitHub holen
[Service]
Type=oneshot
ExecStart=$REPO_DIR/deploy/auto-deploy.sh
EOF
unit investtimer-deploy.timer <<EOF
[Unit]
Description=InvestTimer: Deploy alle 2 Minuten
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
[Install]
WantedBy=timers.target
EOF
unit investtimer-cert.service <<EOF
[Unit]
Description=InvestTimer: HTTPS-Zertifikat holen
[Service]
Type=oneshot
ExecStart=$REPO_DIR/deploy/cert.sh
EOF
unit investtimer-cert.timer <<EOF
[Unit]
Description=InvestTimer: Zertifikat versuchen, bis es da ist
[Timer]
OnBootSec=3min
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now investtimer-data.timer investtimer-deploy.timer >/dev/null

echo "== 4/5 nginx"
if [ -d /etc/nginx/sites-available ]; then
    NGINX_FILE=/etc/nginx/sites-available/investtimer
else
    NGINX_FILE=/etc/nginx/conf.d/investtimer.conf
fi
if [ ! -f "$NGINX_FILE" ] || [ "${1:-}" = "--force-nginx" ]; then
    cp "$REPO_DIR/deploy/nginx.conf" "$NGINX_FILE"
    [ -d /etc/nginx/sites-enabled ] && ln -sf "$NGINX_FILE" /etc/nginx/sites-enabled/investtimer
    if nginx -t 2>/dev/null; then
        systemctl reload nginx
        echo "Block aktiv: $NGINX_FILE"
    else
        rm -f "$NGINX_FILE" /etc/nginx/sites-enabled/investtimer
        echo "FEHLER: nginx-Test fehlgeschlagen, Block wieder entfernt (bestehende Seiten unberuehrt)."
        nginx -t || true
        exit 1
    fi
else
    echo "Block vorhanden, unveraendert ($NGINX_FILE)."
fi

echo "== 5/5 Erster Lauf"
DATA_OK=nein
if (set -a; . "$ENV_FILE"; set +a; python3 "$REPO_DIR/server/update_stress.py"); then DATA_OK=ja; fi
if command -v certbot >/dev/null; then
    systemctl enable --now investtimer-cert.timer >/dev/null
    "$REPO_DIR/deploy/cert.sh" || true
else
    echo "certbot fehlt - HTTPS wird nicht automatisch eingerichtet."
fi
SITE=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: investtimer.net' http://127.0.0.1/ || true)

echo
echo "== Ergebnis"
echo "Seite lokal (erwartet 200 oder 301): $SITE"
echo "Live-Daten: $DATA_OK"
if [ "$DATA_OK" != ja ]; then
    echo "  -> Seite zeigt bis dahin den eingebetteten Stand."
    echo "  -> Der Endpunkt /v1/marktstress fehlt noch in der Volafly-API: Auftrag in"
    echo "     $REPO_DIR/volafly-api/AUFTRAG.md ausfuehren. Der Timer holt den Wert danach von selbst."
fi
echo "Zertifikat: $([ -d /etc/letsencrypt/live/investtimer.net ] && echo vorhanden || echo 'folgt automatisch, sobald DNS auf den Server zeigt')"
