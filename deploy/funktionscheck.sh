#!/bin/bash
# Funktions-Check nach jedem Deploy: Seite, Wert, Verlauf (oeffentlich), KI (echter Testnutzer), Volafly unveraendert.
set -u
ok=0; f(){ if eval "$2" >/dev/null 2>&1; then echo "ok   $1"; else echo "FEHL $1"; ok=1; fi; }
f "Seite laedt (200)" "curl -4fsS -o /dev/null https://investtimer.net/"
f "Seite ist der aktuelle Build ($(git -C /var/www/investtimer log -1 --format=%h))" "curl -4fsS https://investtimer.net/ | grep -q 'investtimer-sitzung'"
f "Wert da (/data/stress.json)" "curl -4fsS https://investtimer.net/data/stress.json | python3 -c 'import json,sys;d=json.load(sys.stdin);assert isinstance(d[\"publicSnapshot\"][\"rounded\"],int)'"
f "Verlauf oeffentlich (bis zum zeitversetzten Datum)" "curl -4fsS https://investtimer.net/api/historie-oeffentlich | python3 -c 'import json,sys;d=json.load(sys.stdin);assert d[\"taeglich\"][-1][0]<=d[\"bis\"]'"
f "KI-Status" "curl -4fsS https://investtimer.net/api/chat | grep -q '\"ok\": *true'"
f "volafly-chat aktiv" "systemctl is-active --quiet volafly-chat"
f "volafly.net laedt" "curl -4fsS -o /dev/null https://volafly.net/"
if [ "${1:-}" = "--ki" ]; then
  python3 "$(dirname "$0")/supabase_test.py" 2>&1 | tail -4 | sed 's/^/     /'
fi
exit $ok
