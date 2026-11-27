#!/bin/bash
# InvestTimer Gesamtpruefung (tests/qa): Funktion, Daten, Sicherheit, Datenschutz, Qualitaet, Betrieb.
# Aufruf: tools/qa_gesamt.sh [--mail] [--mails] [--schnell]
#   --mail    Kurzbericht per Mail an info@investtimer.net (woechentlicher Cron)
#   --mails   zusaetzlich Monitoring-Testmails ausloesen (Betreff "TEST"; nur bei manueller Pruefung)
#   --schnell ohne Lighthouse/axe/check_mobile --voll (Bereich 5 entfaellt)
# Ergebnisse: /var/lib/investtimer/qa/<datum>/ (ergebnisse.jsonl, kurzbericht.md, Lighthouse/axe/KI-Stichproben).
# Nur Testkonten (werden geloescht), nichts wird dauerhaft veraendert. Werkzeuge: /opt/investtimer-qa (venv, node_modules).
set -u
cd "$(dirname "$0")/.."
export QA_AUSGABE=${QA_AUSGABE:-/var/lib/investtimer/qa/$(date +%Y-%m-%d)}
mkdir -p "$QA_AUSGABE"; chmod 700 "$QA_AUSGABE"; rm -f "$QA_AUSGABE/ergebnisse.jsonl"
PY=/opt/investtimer-qa/venv/bin/python
exec > >(tee -a "$QA_AUSGABE/lauf.log") 2>&1
echo "== InvestTimer QA $(date -Is) =="
for m in funktion testumgebung daten sicherheit datenschutz; do
  echo "--- $m"; timeout 3600 nice -n 10 $PY -W ignore tests/qa/$m.py || echo "$m abgebrochen"
done
if [[ " $* " != *" --schnell "* ]]; then
  echo "--- qualitaet"; timeout 7200 nice -n 10 $PY -W ignore tests/qa/qualitaet.py || echo "qualitaet abgebrochen"
fi
echo "--- betrieb"; timeout 1800 $PY -W ignore tests/qa/betrieb.py $([[ " $* " == *" --mails "* ]] && echo --mails) || echo "betrieb abgebrochen"
$PY tests/qa/bericht.py "$QA_AUSGABE" $([[ " $* " == *" --mail "* ]] && echo --mail)
# alte Laeufe aufraeumen (90 Tage)
find /var/lib/investtimer/qa -mindepth 1 -maxdepth 1 -type d -mtime +90 -exec rm -rf {} + 2>/dev/null
