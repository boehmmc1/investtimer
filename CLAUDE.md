# InvestTimer – Arbeitsregeln für Claude

## Dauerregel (von Michel, 17.11.2026)

Aufträge komplett selbst umsetzen: Code, UI, Tests, Git-Push nach `main` und
Deployment. Nur bei echten Entscheidungen fragen (Produkt, Recht, Geld, Daten
Dritter). Am Ende kurz berichten: was live ist, was getestet wurde, was offen ist.

Das gilt als Freigabe für Push nach `main` und für Server-Änderungen an
InvestTimer (nginx-Block `investtimer`, `/etc/investtimer.env`, InvestTimer-Teil
der Volafly-API). Vor jeder Änderung an Server-Dateien eine Sicherung anlegen,
`nginx -t` vor jedem Reload, nach dem Deploy die Live-Seite prüfen.

## Grenzen, die trotzdem gelten

- Volafly selbst (`/chat`, sein Token, Limit, CORS, `vorlagen.py`) nicht anfassen,
  außer der Auftrag sagt es ausdrücklich.
- Geheimnisse nie ausgeben, nie committen, nie in Logs. Ablage nur root-lesbar (0600):
  - Supabase-Zugriffstoken (Management-API): `/root/.investtimer/supabase-token`
  - Datenbank-Passwort: `/root/.investtimer-supabase-db`
  - Resend: voller Schlüssel `/root/.investtimer/resend-key`, Sende-Schlüssel für Supabase-SMTP
    `/root/.investtimer/resend-smtp-key` (Supabase löscht SMTP bei jedem Auth-PATCH ohne SMTP-Felder,
    `supabase_einrichten.py` schickt sie deshalb immer mit)
  - Der `service_role`-Schlüssel wird nicht gespeichert, nur zur Laufzeit über die
    Management-API geholt (Tests mit Admin-API, z. B. `generate_link`).
- Registrieren/Anmelden bleibt öffentlich ausgeblendet, solange
  `public/impressum.html` und `public/datenschutz.html` fehlen (der Build prüft das).
  Die Texte liefert Michel; sie werden nicht selbst formuliert.
- Rechtliche Fragen (Abo, Widerruf, Datenschutz, Anlageberatung) gehen an den
  Skill `investtimer-pruefpartner`, nicht nebenbei entscheiden.

## Betrieb

- Repo `boehmmc1/investtimer`, Live-Checkout `/var/www/investtimer` (nie direkt
  darin arbeiten). Feature-Arbeit im Worktree `/root/investtimer-ki-halbmond`.
- Push: Deploy-Key `/root/.ssh/investtimer_deploy` mit Schreibrecht (Host-Alias `github-investtimer-push`,
  Push-URL im Worktree gesetzt; derselbe Schlüssel holt auch das Auto-Deploy).
  Keine GitHub-Tokens im Chat annehmen oder speichern.
- Deploy: `investtimer-deploy.timer` holt `main` alle 2 Minuten (`git reset --hard`).
- Daten: `investtimer-data.service` schreibt `/var/lib/investtimer/data/stress.json`.
- API: `/root/volafly-chat/volafly_chat.py` (systemd `volafly-chat`, Port 8100,
  kein Git, vor Änderungen `.bak-<datum>` anlegen).
- Seite bauen (live): `python3 tools/build_v12.py source/InvestTimer_UI_Signalbogen_v1.3.html public --anmeldung=deploy/supabase.json`
- Cloudflare-Token: `/root/.investtimer/cloudflare-token` (DNS + Email-Routing-Regeln für investtimer.net, nur über IPv4 nutzbar: `curl -4`).
  Email Routing einschalten darf er nicht (Dashboard).
- Supabase: Projekt `investtimer` (`owcmsgroqhawcjlehcjk`, Frankfurt), öffentliche Werte in `deploy/supabase.json`.
  Eigene deutsche Mailtexte (mit 6-stelligem Code) erst mit eigenem SMTP möglich; dann
  `deploy/supabase_einrichten.py` erneut laufen lassen, setzt `code: true`, Seite neu bauen.
- Web-App und Push: `public/sw.js` (nur Push, kein Cache), Dialog/Installationshinweis in `tools/alarme.js`.
  Alarme und Geräte in SQLite `/var/lib/investtimer/alarme.db` (Modul `volafly-api/investtimer_alarme.py`,
  Kopie neben der API in `/root/volafly-chat/`). Versand `server/push_senden.py` mit Python aus
  `/opt/investtimer-push` (pywebpush), läuft als ExecStartPost von `investtimer-data.service`
  (Drop-in `deploy/systemd/investtimer-data-push.conf`). VAPID-Schlüssel `/root/.investtimer/vapid-*`.
  Push-Test im Browser nur mit festem Profil und Bildschirm: `xvfb-run` + `launch_persistent_context`.
- Prüfen: `python3 tools/check_v12.py` (mobil) und `deploy/supabase_test.py` (Anmeldung echt, mit Admin-API).
- Konto/Premium/Abo: `volafly-api/investtimer_konto.py` (SQLite `/var/lib/investtimer/konto.db`), API-Block
  `volafly-api/investtimer_api_konto.py` (in `volafly_chat.py` vor `/health` eingefuegt), Dialog `tools/konto.js`.
  Schalter in `/root/volafly-chat/.env`: `IT_PREMIUM_PFLICHT`, `IT_PAYWALL`, `IT_ZAHLUNG_LIVE` (alle aus, nur mit Michels
  Freigabe einschalten: Zahlungen/Live-Modus sind Aussenhandlungen). Stand und offene Punkte: `docs/premium-und-app.md`.
  Tests: `python3 -m unittest tests/test_konto.py`.
- iOS-App: `app/` (Capacitor 8, braucht Node 22 unter `/opt/node22/bin`), Build-Ablauf `docs/ios-app.md`,
  GitHub-Workflow `.github/workflows/ios.yml` (Simulator-Build). APNs-Schluessel `/root/.investtimer/apns.json`.
- Browser-Tests laufen mit der Playwright-Umgebung im Scratchpad (`venv/bin/python`); Chrome `/usr/bin/google-chrome`.
- Vertrag/Abo-Mails: `volafly-api/investtimer_vertrag.py` + `investtimer_api_vertrag.py`; Seiten `tools/vertragsseiten.py`
  (Link im Fuss erst mit `deploy/abo.json` vertragsseiten=true). API-Bloecke einbauen: `python3 deploy/api_einbauen.py`
  (Sicherung automatisch), dann `systemctl restart volafly-chat`. Schalter zusaetzlich `IT_ABO_MAILS`.
- Tests Abo-Strecke: `python3 tests/e2e_abo.py` (eigene API-Instanz Port 8199, nachgebaute Dienste Port 12111, Testnutzer
  wird geloescht), `python3 -m unittest tests/test_konto.py tests/test_vertrag.py`.
- Stripe einrichten: Schluessel nach `/root/.investtimer/stripe-key`, dann `python3 deploy/stripe_einrichten.py`.
- Timer: `investtimer-sicherung` (03:15, `/var/backups/investtimer`), `investtimer-abo-erinnerung` (stuendlich).
- Entwuerfe Abo-Rechtstexte: `docs/rechtstexte/entwurf/` (nicht veroeffentlichen ohne Anwaltspruefung).

- Alarme: Ueberqueren mit Ruecklauf (Spalte `scharf`), Kanal push/email/beide, E-Mail ueber Resend von alarm@investtimer.net
  mit signiertem Abmeldelink `/api/alarm-abmelden` (Schluessel `/root/.investtimer/alarm-abmelde-key`). Tests:
  `/opt/investtimer-push/bin/python -m unittest tests/test_alarm_mail.py`.
- Seit 19.11.2026 liegt der gesamte InvestTimer-Teil von `volafly_chat.py` im Repo: Chat, Anmeldung, Alarme, Push in
  `volafly-api/investtimer_api_chat.py` (ab Markierung `# ── InvestTimer-Chat`), dazu Konto, Vertrag, Alarm-Mail.
  Einbauen: `python3 deploy/api_einbauen.py && systemctl restart volafly-chat`. Nie direkt in `volafly_chat.py` aendern.
  Vorbereitete KI-Antworten: `volafly-api/investtimer_antworten.json` (gelesen aus `/var/www/investtimer/volafly-api/`).
- KI: Stilblock in `investtimer_prompt.md`, Stilpruefung im Code (`_it_stil`: Messwerte <= 4, Verbotsliste, Laenge,
  nur bei Verstoss ein Ueberarbeitungsaufruf). Kontingent je Konto `IT_KI_TAG` in `.env` (2, DEC-015).
  KI-Bereich der Seite: `tools/ki.js` (#ki, Tabs, Leiste unten, Kugel, Belege), Fragen `investtimer_fragen.json` -> `ki_ansicht`.
- UI-Vorlage ist jetzt `source/InvestTimer_UI_Signalbogen_v1.3.html`. Der Build lagert alle Base64-Daten nach `public/media/`
  aus und bricht ab, wenn Demo/Entwurf/Vorschau/Beispielantwort oder Base64 in der Seite stehen.
- Verlauf: Rueckrechnung `historie/holen.py` (TradingView-Websocket ueber `/root/volafly-video/fetch_history.py`, CNN Fear & Greed)
  und `historie/rechnen.py` (exakt `marktstress.calculate`, Config `historie/config.json`). Rohdaten und Ergebnis NUR auf dem
  Server unter `/var/lib/investtimer/historie/` (Datenrechte LIC-001, Repo ist oeffentlich). Aufgezeichnete Tage
  (`/var/lib/investtimer/data/history.json`) werden nie ersetzt oder gekuerzt. Timer `investtimer-historie` holt taeglich den S&P 500.
  S&P-500-Anzeige seit 18.11.2026 entfernt (LIC-001), Timer `investtimer-historie` deaktiviert; SPX.csv nur intern fuer SPX_200D.
  Ereignismarken: `historie/ereignisse.json` (`aus: true` blendet aus). KI-Werkzeug `marktstress_verlauf`.
