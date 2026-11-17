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
- Push: SSH-Schlüssel `/root/.ssh/investtimer_push` (Host-Alias `github-investtimer-push`,
  Push-URL im Worktree gesetzt). Muss auf GitHub als Deploy-Key mit Schreibrecht eingetragen sein.
  Keine GitHub-Tokens im Chat annehmen oder speichern.
- Deploy: `investtimer-deploy.timer` holt `main` alle 2 Minuten (`git reset --hard`).
- Daten: `investtimer-data.service` schreibt `/var/lib/investtimer/data/stress.json`.
- API: `/root/volafly-chat/volafly_chat.py` (systemd `volafly-chat`, Port 8100,
  kein Git, vor Änderungen `.bak-<datum>` anlegen).
- Seite bauen (live): `python3 tools/build_v12.py source/InvestTimer_UI_Signalbogen_v1.2.html public --anmeldung=deploy/supabase.json`
- Supabase: Projekt `investtimer` (`owcmsgroqhawcjlehcjk`, Frankfurt), öffentliche Werte in `deploy/supabase.json`.
  Eigene deutsche Mailtexte (mit 6-stelligem Code) erst mit eigenem SMTP möglich; dann
  `deploy/supabase_einrichten.py` erneut laufen lassen, setzt `code: true`, Seite neu bauen.
- Prüfen: `python3 tools/check_v12.py` (mobil) und `deploy/supabase_test.py` (Anmeldung echt, mit Admin-API).
