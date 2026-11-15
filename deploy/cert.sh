#!/usr/bin/env bash
# Holt das HTTPS-Zertifikat, sobald die Domain auf diesen Server zeigt.
# Laeuft alle 15 Minuten und schaltet sich nach Erfolg selbst ab.
set -euo pipefail
DOMAIN=investtimer.net

if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    systemctl disable --now investtimer-cert.timer >/dev/null 2>&1 || true
    echo "Zertifikat vorhanden."
    exit 0
fi

SERVER_IP=$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
resolves_here() { [ "$(getent ahostsv4 "$1" | awk 'NR==1{print $1}')" = "$SERVER_IP" ]; }

if ! resolves_here "$DOMAIN"; then
    echo "$DOMAIN zeigt noch nicht auf $SERVER_IP - warte auf DNS."
    exit 0
fi
DOMAINS=(-d "$DOMAIN")
if resolves_here "www.$DOMAIN"; then DOMAINS+=(-d "www.$DOMAIN"); fi

certbot --nginx --non-interactive --agree-tos --redirect "${DOMAINS[@]}" \
  || certbot --nginx --non-interactive --agree-tos --redirect --register-unsafely-without-email "${DOMAINS[@]}"
systemctl disable --now investtimer-cert.timer >/dev/null 2>&1 || true
echo "Zertifikat eingerichtet: https://$DOMAIN"
