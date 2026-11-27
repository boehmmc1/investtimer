#!/usr/bin/env bash
# Testumgebung (DEC-020): holt Branch test, baut die Seite mit den Schaltern der Testinstanz (Paywall an, Band oben) und baut
# bei geaenderter API die Bloecke in /root/investtimer-test-api ein. Laeuft alle 2 Minuten (investtimer-test-deploy.timer).
set -euo pipefail
cd /var/www/investtimer-test
git fetch --quiet origin test
alt=$(git rev-parse HEAD)
[ "$alt" = "$(git rev-parse origin/test)" ] && [ -f public/.test-gebaut ] && exit 0
git reset --hard --quiet origin/test
IT_ENV_DATEI=/root/investtimer-test-api/.env IT_TESTUMGEBUNG=1 /usr/bin/python3 tools/build_v12.py source/InvestTimer_UI_Signalbogen_v1.3.html public --anmeldung=deploy/supabase.json >/dev/null
touch public/.test-gebaut
if ! git diff --quiet "$alt" HEAD -- volafly-api || [ ! -f /root/investtimer-test-api/.eingebaut ]; then
    python3 deploy/api_einbauen.py /root/investtimer-test-api >/dev/null
    touch /root/investtimer-test-api/.eingebaut
    systemctl restart investtimer-test-api
fi
echo "Test deployt: $(git log -1 --format='%h %s')"
