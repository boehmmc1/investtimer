#!/bin/bash
# Lasttest investtimer.net (schonend): tests/last/lauf.sh <name> ; Ergebnisse /var/lib/investtimer/last/<name>/
# Stufen 50/200/500 oeffentlich, 100 eingeloggt (Testkonten aus konten.py). Abbruch: Fehlerquote > 2 % (k6) oder volafly.net > 3x langsamer.
# Ausserhalb der Scraper-Zeiten starten (Scraper :00/:30, Dauer ca. 4 Min.).
set -u
NAME=${1:-lauf}; D=/var/lib/investtimer/last/$NAME; mkdir -p $D; cd "$(dirname "$0")"
K6=/opt/investtimer-qa/k6; IP=$(curl -4 -s --max-time 5 https://api.ipify.org || echo 187.124.169.24)
echo "$IP 1;" > /etc/nginx/investtimer-lasttest.conf; echo "127.0.0.1 1;" >> /etc/nginx/investtimer-lasttest.conf; nginx -t -q && systemctl reload nginx
trap ': > /etc/nginx/investtimer-lasttest.conf; nginx -t -q && systemctl reload nginx; kill $VPID $SPID 2>/dev/null' EXIT
basis=$(for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{time_total}\n" https://volafly.net/; done | sort -n | sed -n 3p)
echo "volafly.net Basis: ${basis}s" | tee $D/volafly.txt
( n=0; while true; do t=$(curl -s -o /dev/null -w "%{time_total}" --max-time 10 https://volafly.net/); echo "$(date -u +%T) $t" >> $D/volafly.txt
  if awk -v t=$t -v b=$basis 'BEGIN{exit !(t>3*b && t>0.5)}'; then n=$((n+1)); else n=0; fi
  if [ $n -ge 2 ]; then echo "ABBRUCH: volafly.net ${t}s (2x in Folge > 3x Basis)" >> $D/volafly.txt; pkill -INT k6; n=0; fi
  rss=$(ps -o rss= -p $(systemctl show -p MainPID --value volafly-chat) | awk '{print int($1/1024)}')
  if [ "${rss:-0}" -gt 1200 ]; then echo "ABBRUCH: API-Speicher ${rss} MB" >> $D/volafly.txt; pkill -INT k6; fi
  sleep 3; done ) & VPID=$!
( while true; do echo "$(date -u +%T) $(cut -d' ' -f1 /proc/loadavg) $(vmstat 1 2 | tail -1 | awk '{print $13+$14, $4/1024}') $(ps -C uvicorn -o rss= | sort -n | tail -1 | awk '{print int($1/1024)}')" >> $D/system.txt; sleep 4; done ) & SPID=$!
for n in 50 200 500; do
  echo "== oeffentlich $n"; $K6 run -q -e STUFE=$n --summary-export=$D/oeffentlich-$n.json oeffentlich.js > $D/oeffentlich-$n.txt 2>&1; echo "rc=$?" >> $D/oeffentlich-$n.txt
  grep -q ABBRUCH $D/volafly.txt && break; sleep 20
done
if [ -f /var/lib/investtimer/last/konten.json ] && ! grep -q ABBRUCH $D/volafly.txt; then
  TOKENS=$(python3 -c "import json;print(','.join(x['token'] for x in json.load(open('/var/lib/investtimer/last/konten.json'))))")
  echo "== eingeloggt 100"; $K6 run -q -e STUFE=100 -e TOKENS=$TOKENS --summary-export=$D/eingeloggt-100.json eingeloggt.js > $D/eingeloggt-100.txt 2>&1; echo "rc=$?" >> $D/eingeloggt-100.txt
fi
echo fertig
