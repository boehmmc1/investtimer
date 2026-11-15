#!/usr/bin/env bash
# Holt den Stand von main. Laeuft alle 2 Minuten (investtimer-deploy.timer).
set -euo pipefail
cd /var/www/investtimer
git fetch --quiet origin main
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    git reset --hard --quiet origin/main
    echo "deployt: $(git log -1 --format='%h %s')"
fi
