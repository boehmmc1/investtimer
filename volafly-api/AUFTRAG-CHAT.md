# Auftrag: InvestTimer-Chat in der Volafly-API

Auftragstext für Claude Code auf dem Server (Ordner `/root/volafly-chat`).
Voraussetzung: Der Auftrag `AUFTRAG.md` (Endpunkt `/v1/marktstress`) ist erledigt.

---

Ergänze das FastAPI-Backend `volafly_chat.py` um einen zweiten, öffentlichen
Chat-Zugang für investtimer.net. Er nutzt dieselbe Pipeline wie `/chat`
(Modell, Werkzeuge, Prompt-Caching, Vorlagen-Sparpfad), aber mit eigenem
Profil, kleinerem Themenkreis und ohne Login.

**Endpunkte**

- `GET /v1/investtimer/chat` → `{"ok": true}`. Ist der Chat abgeschaltet
  (`INVESTTIMER_CHAT=off` in der `.env`), stattdessen `503`. Die Seite blendet
  den KI-Bereich nur ein, wenn hier `ok` kommt.
- `POST /v1/investtimer/chat` mit `{"frage": str, "verlauf": [{role, content}]}`
  → `{"antwort": str}`. Gleiches Format wie `/chat`.

Aufgerufen wird nur über nginx von investtimer.net (`/api/chat` →
`127.0.0.1:8100/v1/investtimer/chat`, gleiche Herkunft, daher keine
CORS-Änderung). nginx setzt `X-Real-IP`.

**Zugang und Grenzen** (als Konstanten oben im Code, je eine Zeile zum Ändern)

- Kein Supabase-Token.
- 10 Fragen pro Tag und IP (aus `X-Real-IP`, nur wenn die Anfrage von
  127.0.0.1 kommt), 300 Fragen pro Tag insgesamt. Bei Überschreitung `429`.
- Frage höchstens 300 Zeichen, Verlauf auf die letzten 6 Nachrichten gekappt.
- Fragen aus dem Vorlagen-Sparpfad, die ohne Modellaufruf beantwortet werden,
  zählen nicht gegen das Gesamtlimit.

**Profil**

- System-Prompt: Der Stilblock des Volafly-Chats wird für diesen Endpunkt
  durch `/var/www/investtimer/volafly-api/investtimer_prompt.md` ersetzt
  (Text unter der Trennlinie). Werkzeuge und Quellenregel bleiben.
- Live-Daten-Werkzeug: nur die Zeilen, die zu den 14 Bestandteilen gehören,
  plus das Ergebnis von `marktstress.payload_from_rows(...)` (Wert, Anzahl,
  Anteile). Keine übrigen Sheet-Zeilen.
- Wissensbasis-Werkzeug: nur die Themen-Dateien zu Volatilität,
  Marktindikatoren und Lehren aus Marktphasen. Keine Strategie-, Regelwerks-
  und Kontraktauswahl-Dateien.
- Musterfragen: `/var/www/investtimer/volafly-api/investtimer_fragen.json`.
  - `quelle: katalog` steht wortgleich in `fragen_templates.json`. Diese
    Fragen laufen über den vorhandenen Sparpfad.
  - Fertige Antworten und Vorlagen, die Stillhalter-Perspektive,
    Optionsstrategien, „Volafly“ oder „Magazin“ enthalten, bekommen für
    InvestTimer eine neutrale Fassung nach dem Profil. Lege diese Fassungen
    in `investtimer_antworten.json` ab; der InvestTimer-Endpunkt nimmt sie
    vorrangig. Die Volafly-Fassungen bleiben unverändert.
  - `quelle: neu` (3 Fragen) gibt es im Katalog nicht. Lege für die beiden
    Fragen mit `art: wissen` fertige Antworten und für die Frage mit
    `art: live` eine Vorlage in `investtimer_antworten.json` an.

**Unverändert bleiben** `/chat`, dessen Token-Prüfung, Tageslimit und CORS.

**Vorgehen**

- Vorher: Sicherung `volafly_chat.py.bak-<Datum>`, Funktionstest des
  Volafly-Chats notieren.
- Nachher: `systemctl restart volafly-chat`, dann prüfen:
  - `curl -s http://127.0.0.1:8100/v1/investtimer/chat` → `{"ok":true}`
  - je eine Katalog-Frage (`live` und `wissen`), eine neue Frage, eine freie
    Frage im Thema, eine Frage außerhalb des Themas (z. B. nach einem Short
    Put) → Antworten im Profil, Ablehnung beim letzten Fall
  - keine Antwort enthält „Volafly“, „Stillhalter“, „Magazin“, Anker oder
    Datenquellen
  - 11. Frage von derselben IP → `429`
  - `curl -s https://investtimer.net/api/chat` → `{"ok":true}`
  - Volafly-Chat-Test wie vorher → unverändert
- Schlägt ein Test fehl: Sicherung zurückspielen, Dienst neu starten,
  Volafly-Test wiederholen, Fehler berichten.
- `[usage]`-Zeilen im Journal für diesen Endpunkt mit `investtimer` kennzeichnen.
- Am Ende berichten: geänderte Stellen, Testergebnisse, und den vollen Text
  aller Antworten in `investtimer_antworten.json` zur Durchsicht.
