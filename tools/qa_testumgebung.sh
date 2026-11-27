#!/bin/bash
# Naechtliche Pruefung der Testumgebung (Nachtrag N5): tests/qa/testumgebung.py (Bearer-Token eines kurzlebigen Testkontos gegen
# test.investtimer.net, Kontoloeschung -> alter Token 401, nginx /api/ ohne Basic-Auth). Mail an info@ nur bei Befunden.
# Laeuft ueber investtimer-qa-test.timer (taeglich 04:40 UTC, aus dem Checkout der Testumgebung) und in tools/qa_gesamt.sh.
set -u
cd "$(dirname "$0")/.."
export QA_AUSGABE=/var/lib/investtimer/qa-test/$(date +%Y-%m-%d)
mkdir -p "$QA_AUSGABE"; chmod 700 "$QA_AUSGABE"; rm -f "$QA_AUSGABE/ergebnisse.jsonl"
PY=/opt/investtimer-qa/venv/bin/python
export QA_BETREFF_PRAEFIX="TEST Testumgebung – "
timeout 900 $PY -W ignore tests/qa/testumgebung.py > "$QA_AUSGABE/lauf.log" 2>&1 || echo "testumgebung abgebrochen" >> "$QA_AUSGABE/lauf.log"
if ! [ -s "$QA_AUSGABE/ergebnisse.jsonl" ] || grep -q '"ok": false' "$QA_AUSGABE/ergebnisse.jsonl"; then
  [ -s "$QA_AUSGABE/ergebnisse.jsonl" ] || echo '{"zeit":"","bereich":"1 Funktion","name":"Pruefung Testumgebung gelaufen","ok":false,"schwere":"hoch","nachweis":"tools/qa_testumgebung.sh","info":"keine Ergebnisse"}' > "$QA_AUSGABE/ergebnisse.jsonl"
  $PY tests/qa/bericht.py "$QA_AUSGABE" --mail
fi
find /var/lib/investtimer/qa-test -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null
exit 0
