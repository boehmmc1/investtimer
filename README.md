# InvestTimer

Statische Seite für investtimer.net. Zeigt den Marktstress (0–100).

## Aufbau

| Pfad | Zweck |
|---|---|
| `public/index.html` | Die Seite (kein Build-Schritt) |
| `server/update_stress.py` | Holt das Ergebnis von der Volafly-API, schreibt `stress.json` |
| `volafly-api/marktstress.py` | Rechenkern für den API-Endpunkt `GET /v1/marktstress` |
| `volafly-api/AUFTRAG.md` | Auftragstext zum Einbau des Endpunkts in die Volafly-API |
| `deploy/setup.sh` | Einmalige Server-Einrichtung (wiederholbar) |
| `deploy/auto-deploy.sh` | Holt `main` alle 2 Minuten |
| `deploy/cert.sh` | Holt das HTTPS-Zertifikat, sobald DNS stimmt |
| `deploy/nginx.conf` | nginx-Block |
| `public/apple-touch-icon.png`, `public/og-image.png` | Homescreen-Icon, Vorschaubild für geteilte Links |
| `ui/ki.html`, `ui/ki.css`, `ui/ki.js` | KI-Bereich (Fragenkarten, Autocomplete, Chat) |
| `volafly-api/investtimer_fragen.json` | Musterfragen: einzige Quelle für Seite und Backend |
| `volafly-api/investtimer_prompt.md` | Themen- und Stilprofil des InvestTimer-Chats |
| `volafly-api/AUFTRAG-CHAT.md` | Auftragstext zum Einbau des Chat-Endpunkts in die Volafly-API |
| `source/` | Unveränderter UI-Export (wird nicht ausgeliefert) |
| `tools/build_public.py` | Baut `public/index.html` aus dem UI-Export (Live-Daten, Mobil-Nachschärfung) |
| `tools/check_mobile.py` | Mobil-Prüfung: 6 Bildschirmgrößen × 9 Ansichten |

## Zwei Seitenstände

| Adresse | Quelle | Build |
|---|---|---|
| `/` (live) | UI-Export v1.0 + KI-Bereich aus `ui/` | `tools/build_public.py`, Prüfung `tools/check_mobile.py` |
| `/neu/` (Vorschau, noindex) | UI-Export v1.2: öffentliche Ansicht mit zeitversetztem Wert, Ansicht nach Login mit aktuellem Wert und KI-Dialog, Erklärfilm | `tools/build_v12.py`, Prüfung `tools/check_v12.py` |

```bash
python3 tools/build_v12.py source/InvestTimer_UI_Signalbogen_v1.2.html public/neu --vorschau
python3 tools/check_v12.py neu/
```

Live schalten: denselben Build ohne `--vorschau` nach `public` schreiben. Solange
es keine echte Anmeldung gibt, ist „Nach Login" ein Ansichtswechsel und keine
Zugriffssperre: Der aktuelle Wert steht weiter in `/data/stress.json`.

`stress.json` enthält seit v1.2 zusätzlich `publicSnapshot`: den Stand, der
mindestens `PUBLIC_DELAY_DAYS` (Standard 7) alt ist. Der Tagesverlauf dafür
liegt in `/var/lib/investtimer/data/history.json` (nicht ausgeliefert), der
Startwert in `server/seed_history.json`.

## Ablauf

- **Deploy:** Push auf `main` → spätestens 2 Minuten später live.
- **Daten:** Die Volafly-API liefert unter `https://api.volafly.net/v1/marktstress`
  das fertige Ergebnis (Wert, Anzahl, Anteile). InvestTimer holt es alle
  10 Minuten ab und legt es als `/var/lib/investtimer/data/stress.json` ab.
  InvestTimer kennt weder Rohwerte noch Anker noch die Datenquelle.
- **KI-Chat:** Die Seite ruft `/api/chat` auf; nginx reicht das an die
  Volafly-API weiter (`/v1/investtimer/chat`). Der KI-Bereich erscheint nur,
  wenn der Endpunkt antwortet, und nur in der deutschen Ansicht. Abschalten:
  `INVESTTIMER_CHAT=off` in der `.env` der API.
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
journalctl -u investtimer-data.service -n 20   # letzte Abrufe
systemctl start investtimer-data.service       # sofort neu abrufen
bash /var/www/investtimer/deploy/setup.sh --force-nginx   # nginx-Block neu einspielen
```

Änderungen an `deploy/nginx.conf` oder an den Timern greifen erst nach erneutem
`setup.sh`. Alles andere greift mit dem Push.

## Neuer UI-Export

```bash
python3 tools/build_public.py source/NeuerExport.html public/index.html
python3 tools/check_mobile.py     # muss "keine Auffaelligkeiten" melden
```

Änderungen an der Seite gehören in `tools/build_public.py`, nicht direkt in
`public/index.html` – sonst gehen sie beim nächsten Export verloren.
