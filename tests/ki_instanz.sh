#!/bin/bash
# Eigene API-Instanz fuer KI-Tests (Port 8198): liest Prompt, Fragen und vorbereitete Antworten aus dem Arbeitsstand
# (Standard: dieses Repo), Anmeldung aus (kein Konto-Kontingent). Aufruf: tests/ki_instanz.sh start|stop [quellordner]
set -e
DIR=/tmp/investtimer-ki-instanz
QUELLE=${2:-$(cd "$(dirname "$0")/.." && pwd)}
if [ "$1" = stop ]; then pkill -f "[u]vicorn volafly_chat:app --host 127.0.0.1 --port 8198" 2>/dev/null; sleep 1; rm -rf $DIR; exit 0; fi
rm -rf $DIR; mkdir -p $DIR; chmod 700 $DIR
for f in /root/volafly-chat/*.py /root/volafly-chat/*.json; do ln -s "$f" $DIR/; done
rm -f $DIR/volafly_chat.py $DIR/investtimer_konto.py $DIR/investtimer_alarme.py $DIR/investtimer_vertrag.py $DIR/investtimer_ki_limit.py $DIR/investtimer_ki_preise.json
cp /root/volafly-chat/volafly_chat.py $DIR/volafly_chat.py
python3 "$QUELLE/deploy/api_einbauen.py" $DIR >/dev/null   # Arbeitsstand der InvestTimer-Bloecke, nur in der Kopie
rm -f $DIR/volafly_chat.py.bak-*
sed -i "s#/var/www/investtimer/volafly-api/#$QUELLE/volafly-api/#g" $DIR/volafly_chat.py
grep '^IT_\|^INVESTTIMER' /root/volafly-chat/.env | grep -v '^IT_SUPABASE' > $DIR/it.env; chmod 600 $DIR/it.env
(cd $DIR && IT_FEHLER_DB=$DIR/fehler.db IT_KI_DB=$DIR/ki.db IT_ENV_DATEI=$DIR/it.env nohup /usr/local/bin/uvicorn volafly_chat:app --host 127.0.0.1 --port 8198 > $DIR/log 2>&1) < /dev/null > /dev/null 2>&1 &
echo $! > $DIR/pid
for i in $(seq 40); do curl -fs http://127.0.0.1:8198/v1/investtimer/chat >/dev/null 2>&1 && { echo "bereit"; exit 0; }; sleep 1; done
echo "startet nicht"; tail -20 $DIR/log; exit 1
