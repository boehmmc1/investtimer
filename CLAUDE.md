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
- Web-App und Push: Service Worker aus `tools/sw.js` (Build schreibt `public/sw.js` mit Version, Cache: Seite/Wert Netz zuerst, /media/<hash> Cache zuerst, /api nie; Push), Update-Hinweis/Offline in `tools/update.js`, Dialog/Installationshinweis in `tools/alarme.js`.
  Alarme und Geräte in SQLite `/var/lib/investtimer/alarme.db` (Modul `volafly-api/investtimer_alarme.py`,
  Kopie neben der API in `/root/volafly-chat/`). Versand `server/push_senden.py` mit Python aus
  `/opt/investtimer-push` (pywebpush), läuft als ExecStartPost von `investtimer-data.service`
  (Drop-in `deploy/systemd/investtimer-data-push.conf`). VAPID-Schlüssel `/root/.investtimer/vapid-*`.
  Push-Test im Browser nur mit festem Profil und Bildschirm: `xvfb-run` + `launch_persistent_context`.
- Prüfen: `tools/check_mobile.py` mit Playwright-Python (UI-Testreihe `tests/ui/`, nachgespielte API `tests/ui/harness.py`, `--voll` = 9 Größen) und `deploy/supabase_test.py` (Anmeldung echt). Nach jedem Deploy `deploy/funktionscheck.sh --ki`.
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
- Stand 19.11.2026 (Änderungsauftrag): Ansichten #ki/#verlauf/#konto (Routing in `tools/ki.js`, Konto `tools/kontoansicht.js`), Build-Schritte
  `tools/startseite.py` (keine Gewichte), `tools/erklaerungen.py` (Alltagssprache), `tools/farbskala.py` (5 Stufen à 20), CSS `tools/ansichten.css`.
  KI-Einstieg außerhalb des KI-Tabs nur über die KI-Brücke. Mit Sitzung nie den öffentlichen Wert zeigen (gespeicherter Wert `investtimer-aktuell`).
  Film aus (IT_FILM=0, zeigt S&P-500-Kurse). KI-Tests ohne Kontingent: `tests/ki_instanz.sh start` + `tests/ki_fragen.py`.
- Stand 19.11.2026 nachts: Feedback (#feedback, `tools/feedback.js`, API `volafly-api/investtimer_api_feedback.py`), FAQ (#faq, `tools/faq.js` + `tools/faq.json`,
  Abo-Fragen nur mit IT_PAYWALL), Aktualität + Fehlererfassung (`tools/aktualitaet.js`, API `investtimer_api_fehler.py`, DB `/var/lib/investtimer/fehler.db`),
  Vorschaubild `server/og_bild.py` (Timer investtimer-og), Statistik `server/statistik.py` (Timer investtimer-statistik/-wochenbericht, Zugang
  `/root/.investtimer/statistik-zugang`, nginx-Snippet `/etc/nginx/investtimer-statistik.conf` nur auf dem Server). Narrativ hinter IT_NARRATIV (aus).
- KI-Limit seit 20.11.2026 (DEC-016): Modul `volafly-api/investtimer_ki_limit.py` (SQLite `/var/lib/investtimer/ki.db`, `IT_KI_DB` ueberschreibt),
  Preise `volafly-api/investtimer_ki_preise.json`. Freie Fragen: `IT_KI_TAG` (1) je Konto, `IT_KI_IP_TAG` (3) je IP (nur Arbeitsspeicher, wie in der
  Datenschutzerklaerung), `INVESTTIMER_CHAT_TAGESLIMIT` (150) gesamt, Tag = Europe/Berlin. Beispiel-/Folge-/Ereignisfragen (feste Liste aus
  `investtimer_fragen.json` ki_ansicht + `historie/ereignisse.json`) zaehlen nicht, Modell ohne Denken + effort low, Tages-Cache in ki.db.
  Jeder Modellaufruf ueber `_it_usage` (usage-Zeile + Kostenbuchung). Kostenmail `IT_KI_KOSTEN_TAG_EUR`/`IT_KI_KOSTEN_MONAT_EUR` an `IT_KI_KOSTEN_AN`,
  Pause ab 2x Tagesschwelle. Tests: `tests/test_ki_limit.py`, `tests/test_ki_limit_api.py` (ohne Kosten, nachgebaute Dienste), `tests/ui/test_ki_limit.py`.
- Teilen seit 20.11.2026: Bilder `server/teilen_bilder.py` (Chrome headless, 84 Bilder je zeitversetztem Stand in `/var/lib/investtimer/teilen/<asOf>/`,
  Symlink `aktuell`, manifest.json; Timer `investtimer-teilen` stuendlich, rendert nur Fehlendes). API-Block `volafly-api/investtimer_api_teilen.py`:
  `/api/teilen/bild` (302 auf Datei; mit `IT_TEILEN_AKTUELL=1` + Login aktueller Stand, privat, je Tag), `/s/wert|verlauf|phase/...` (og/twitter-Tags,
  Weiterleitung mit ?z= / ?phase= / lang=en und utm). Frontend `tools/teilen.js` (Knoepfe, navigator.share, Dialog), Startparameter in `tools/verlauf.js`.
  nginx-Bloecke in `deploy/nginx.live.conf` (= /etc/nginx/sites-available/investtimer). Tests: `tests/ui/test_teilen.py`, Teilen-Teil in `tests/test_ki_limit_api.py`.
- QA seit 20.11.2026: `tools/qa_gesamt.sh` [--mail] [--mails] [--schnell] fuehrt `tests/qa/{funktion,daten,sicherheit,datenschutz,qualitaet,betrieb}.py` nacheinander aus
  (Werkzeuge /opt/investtimer-qa: venv mit Playwright, node_modules mit lighthouse/axe-core), Ergebnisse /var/lib/investtimer/qa/<datum>/, Kurzbericht `tests/qa/bericht.py`.
  Timer `investtimer-qa` sonntags 06:00 Europe/Berlin (nur Kurzbericht per Mail). Nur Testkonten (qa-*@investtimer.net, werden geloescht). QA-Laeufe nie parallel
  zu anderen Browser-Tests (1 CPU-Kern, sonst falsche Befunde). Sicherheits-Header: Snippet `deploy/nginx-snippets/investtimer-sicherheit.conf`
  (/etc/nginx/snippets/), in server und JEDER location mit eigenem add_header einbinden (nginx 1.18 vererbt sonst nicht).
- Belastbarkeit 20.11.2026: Lasttest `tests/last/lauf.sh <name>` (k6 in /opt/investtimer-qa, Testkonten `tests/last/konten.py anlegen|loeschen`,
  nur ausserhalb :00-:05/:30-:35, Abbruch bei Fehlern/Volafly langsam/API > 1,2 GB). Ratenlimits per Schluessel `$it_limit_key`; Ausnahme nur waehrend
  Lasttests ueber /etc/nginx/investtimer-lasttest.conf (sonst leer!). Limit-Zonen heissen it_chat/it_api: Key einer bestehenden Zone NIE aendern
  (nginx verwirft dann jeden Reload still) – neue Zone mit neuem Namen anlegen und nach Reload `ps -o lstart -C nginx` (Worker-Startzeit) pruefen.
  Externe Erreichbarkeit: .github/workflows/erreichbarkeit.yml (alle 5 Min., Fehler -> GitHub-Mail an den Repo-Inhaber).
- Teilen v2 (20.11.2026 abends): IT_TEILEN_AKTUELL=1 (Michel). Eingeloggt: `/api/teilen/stand` (gleiche Quelle wie /api/aktuell, `_it_aktuell_roh`) und
  `/api/teilen/bild?aktuell=1` rendern je Wert+Zeitstempel einmal nach `/var/lib/investtimer/teilen/live/<JJJJ-MM-TTTHHMM>/` (oeffentlich, 30 Tage),
  Links `/s/wert/<stamp>`, `/s/verlauf/<Z>/<stamp>` (og:image = geteiltes Bild, fehlendes Querformat wird nachgerendert), Ziel `?geteilt=..&st=..` -> Band.
  Verlauf-Endpunkt eingeloggt = IT.live (`vMitAktuell` in tools/verlauf.js). Neue API-Pfade brauchen eine eigene nginx-Location (UI-Tests sehen das nicht!).
- Verlauf erkunden (20.11.2026): Werte-Zeile `.verlauf-wertzeile` ueber dem Chart, Pointer-Events + rAF + binaere Suche (`vPos`, `vNaechster`),
  keine Textauswahl/Callout. Teilen: Timer `investtimer-teilen-live` (POST /v1/investtimer/teilen/vorab, nur lokal) erzeugt nach jeder Berechnung
  24 Bilder; PNG-Optimierung ueber /opt/investtimer-bild (Pillow, getrennt vom System-Python); Vorladen in tools/teilen.js (`IT.teilenVorladen`).
  Messung: `tests/last/teilen_zeit.py [--drossel]`.
- Alarme Startseite (20.11.2026): tools/alarmblatt.js (Karte #alarm-karte, Blatt/Liste als <dialog class="alarm-blatt">, Marken am Bogen,
  IT.alarmNeu/alarmListe/alarmBearbeiten, Event investtimer:alarme). Zustaende bereit/ausgeloest/pausiert (API-Feld `zustand`).
  Grenze 3 je Richtung (JE_RICHTUNG, Fehler `richtung_voll`), Bestand mit mehr bleibt. Alter Dialog in alarme.js nur noch fuer
  „Mitteilungen auf diesem Geraet“ (IT.oeffneMitteilungen). Harness nutzt die echte investtimer_alarme.py (harness.alarme_setzen).
  Grautext klein: var(--sub), nicht #6e7b74 (Kontrast < 4,5).
- Testumgebung test.investtimer.net (DEC-020, 26.11.2026): Branch `test`, Checkout /var/www/investtimer-test (Timer investtimer-test-deploy,
  baut mit /root/investtimer-test-api/.env: Paywall/Premium-Pflicht/Abo-Mails an, Band "TESTUMGEBUNG"), API investtimer-test-api auf 8101
  (Kopie unter /root/investtimer-test-api, eigene SQLite unter /var/lib/investtimer-test, MemoryMax 400M), Mails nur ueber den Filter
  /v1/test/resend ([TEST], nur info@ und IT_TEST_EMPFAENGER). nginx aus deploy/testumgebung/nginx_test.py, Basic-Auth
  /etc/nginx/investtimer-test.htpasswd (legt Michel an), vom Server selbst ohne Passwort.
  REGEL: Aenderungen an Konto, Abo, Bezahlung, Paywall, Kuendigung, Widerruf, Abo-Mails und Rechtstexten erst auf Branch test,
  Tests auf test.investtimer.net gruen, dann Michel melden; erst nach seinem "passt" nach main. Alles andere direkt nach main.
- Browser-Tests nacheinander (tests/ui/testlauf.py: Sperre, nie waehrend des Scrapers :00/:30, Test-Chrome danach beenden).
- Ausgeloggt: 30 Tage Verzoegerung (PUBLIC_DELAY_DAYS=30, DEC-018), Verlauf hoechstens 1 Jahr (DEC-019). Teilwerte `bloecke` aus
  marktstress.calculate, in history.json/stress.json/publicSnapshot.
