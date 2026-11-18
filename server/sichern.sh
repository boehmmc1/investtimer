#!/bin/sh
# Taegliche Sicherung der InvestTimer-Daten (Konten/Abo-Stand, Alarme, Verlauf).
# Konsistente SQLite-Kopie ueber die Backup-API, 14 Tage aufbewahrt, nur root lesbar.
set -eu
QUELLE=/var/lib/investtimer
ZIEL=/var/backups/investtimer
TAG=$(date +%F)
umask 077
mkdir -p "$ZIEL"
for db in konto alarme; do
  [ -f "$QUELLE/$db.db" ] || continue
  python3 -c "import sqlite3,sys;s=sqlite3.connect(sys.argv[1]);d=sqlite3.connect(sys.argv[2]);s.backup(d);d.close();s.close()" \
    "$QUELLE/$db.db" "$ZIEL/$db-$TAG.db"
  python3 -c "import sqlite3,sys;r=sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0];sys.exit(r!='ok')" "$ZIEL/$db-$TAG.db"
done
[ -f "$QUELLE/data/history.json" ] && cp "$QUELLE/data/history.json" "$ZIEL/history-$TAG.json"
[ -f "$QUELLE/historie/rueckrechnung.json" ] && gzip -c "$QUELLE/historie/rueckrechnung.json" > "$ZIEL/rueckrechnung-$TAG.json.gz"
find "$ZIEL" -type f -mtime +14 -delete
echo "Sicherung $TAG: $(ls "$ZIEL" | grep -c "$TAG") Dateien"
