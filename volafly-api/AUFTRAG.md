# Auftrag: Endpunkt GET /v1/marktstress in der Volafly-API

Auftragstext für Claude Code auf dem Server (Ordner `/root/volafly-chat`).

---

Ergänze das bestehende FastAPI-Backend `volafly_chat.py` (systemd-Dienst
`volafly-chat`, 127.0.0.1:8100, öffentlich unter https://api.volafly.net) um
einen öffentlichen Endpunkt `GET /v1/marktstress`. Abnehmer ist investtimer.net.

**Vorgaben**

1. Kopiere `/var/www/investtimer/volafly-api/marktstress.py` nach
   `/root/volafly-chat/marktstress.py`. Der Rechenkern bleibt unverändert.
2. Der Endpunkt nutzt den vorhandenen Sheet-Zugriff des Backends samt Cache
   (120 s). Er braucht die Zeilen des Haupt-Reiters (Spalten `Metric`, `Value`)
   und des Reiters `Stress_Config` (Spalten `name`, `lo`, `hi`, `weight`). Wird
   `Stress_Config` bisher nicht gelesen, ergänze diesen Lesebereich. Baue keinen
   zweiten Zugriffsweg auf das Sheet.
3. Antwort: `marktstress.payload_from_rows(metric_rows, config_rows)` als JSON.
   Das sind ausschließlich `model`, `asOf`, `updatedAt`, `rounded`, `count`,
   `total`, `rows[{name, effectiveWeight}]`, `blocks[{name, effectiveWeight}]`.
   Keine Rohwerte, keine Anker, keine Quellenangaben, keine Fehlerdetails.
4. Kein Login, kein Tageslimit für diesen Endpunkt. Bei jedem Fehler
   `503` mit `{"error":"unavailable"}`.
5. Der Chat (`/chat`), seine Token-Prüfung, das Tageslimit und die
   CORS-Einstellung bleiben unverändert.

**Vorgehen**

- Vorher: Sicherung `volafly_chat.py.bak-<Datum>` anlegen und einen
  Funktionstest des Chats notieren (Dienst aktiv, `/chat` ohne Token → 401).
- Nachher: `systemctl restart volafly-chat`, dann prüfen:
  - `curl -s http://127.0.0.1:8100/v1/marktstress` → JSON mit `rounded` 0–100
  - `curl -s https://api.volafly.net/v1/marktstress` → dasselbe
  - Chat-Test wie vorher → unverändert
  - `systemctl start investtimer-data.service && journalctl -u investtimer-data.service -n 3`
    → Zeile „Marktstress … geschrieben“
- Schlägt ein Test fehl: Sicherung zurückspielen, Dienst neu starten, Chat-Test
  wiederholen, Fehler berichten.
- Am Ende kurz berichten: geänderte Stellen, Testergebnisse, aktueller Wert,
  fehlende Bestandteile (falls `count` < 14, welche Sheet-Keys fehlen).
