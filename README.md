# InvestTimer

Statische Seite für investtimer.net. Zeigt den Marktstress (0–100).

## Aufbau

| Pfad | Zweck |
|---|---|
| `public/index.html` | Die Seite (kein Build-Schritt) |
| `server/update_stress.py` | Berechnet den Wert auf dem Server, schreibt `stress.json` |
| `deploy/setup.sh` | Einmalige Server-Einrichtung (wiederholbar) |
| `deploy/auto-deploy.sh` | Holt `main` alle 2 Minuten |
| `deploy/cert.sh` | Holt das HTTPS-Zertifikat, sobald DNS stimmt |
| `deploy/nginx.conf` | nginx-Block |
| `tools/build_public.py` | Baut `public/index.html` aus einem neuen UI-Export |

## Ablauf

- **Deploy:** Push auf `main` → spätestens 2 Minuten später live.
- **Daten:** Alle 10 Minuten rechnet der Server den Wert und schreibt
  `/var/lib/investtimer/data/stress.json`. Öffentlich sind nur Wert, Anzahl und
  Anteile. Rohwerte, Anker und Datenquelle bleiben auf dem Server
  (`/etc/investtimer.env`, nicht im Repo).
- **Ausfall:** Kommt keine neue Datei, bleibt der letzte Stand stehen. Fehlt die
  Datei ganz, zeigt die Seite den eingebetteten Stand.

## Ersteinrichtung auf dem Server

```bash
bash <<'EOF'
set -e
K=/root/.ssh/investtimer_deploy
[ -f $K ] || ssh-keygen -t ed25519 -N "" -C investtimer-deploy -f $K -q
echo; echo "Diesen Schlüssel eintragen unter https://github.com/boehmmc1/investtimer/settings/keys/new :"; cat $K.pub; echo
export GIT_SSH_COMMAND="ssh -i $K -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
until git ls-remote git@github.com:boehmmc1/investtimer.git >/dev/null 2>&1; do sleep 10; done
[ -d /var/www/investtimer/.git ] || git clone -q git@github.com:boehmmc1/investtimer.git /var/www/investtimer
bash /var/www/investtimer/deploy/setup.sh
EOF
```

## Nützlich auf dem Server

```bash
systemctl list-timers 'investtimer-*'          # laufen die Timer?
journalctl -u investtimer-data.service -n 20   # letzte Berechnungen
systemctl start investtimer-data.service       # sofort neu rechnen
bash /var/www/investtimer/deploy/setup.sh --force-nginx   # nginx-Block neu einspielen
```

Änderungen an `deploy/nginx.conf` oder an den Timern greifen erst nach erneutem
`setup.sh`. Alles andere greift mit dem Push.

## Neuer UI-Export

```bash
python3 tools/build_public.py NeuerExport.html public/index.html
```
