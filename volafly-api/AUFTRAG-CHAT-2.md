# Auftrag: Nacharbeiten am InvestTimer-Chat

Auftragstext für Claude Code auf dem Server (Ordner `/root/volafly-chat`).
Vorher `git -C /var/www/investtimer log -1 --format=%s` prüfen: Der letzte
Commit muss „Chat-Nacharbeiten“ im Betreff tragen (sonst bis zu 2 Minuten
warten, der Deploy-Timer holt ihn).

---

Drei kleine Änderungen. Sicherung vorher, Tests nachher, bei Fehlschlag
zurückspielen. `/chat` (Volafly) bleibt unverändert.

**1. Einstufung in Vorlage it01 an die Seite angleichen**

Die Seite stuft den Wert in vier Stufen ein, nicht in Dritteln:

| Wert | Stufe auf der Seite |
|---|---|
| unter 25 | Ruhig |
| 25 bis 49 | Moderat |
| 50 bis 74 | Erhöht |
| ab 75 | Hoch |

Vorlage neu: „Der Marktstress liegt aktuell bei {{wert}} von 100. Das
entspricht der Stufe „{{stufe}}“ auf einer Skala von extremer Ruhe (0) bis
extremem Stress (100). {{treiber}} {{vollstaendigkeit}}“. Die Drittel-Texte
entfallen. Auch freie Antworten sollen, wenn sie den Wert einstufen, diese
vier Stufen verwenden (ein Satz dazu im Profil-Prompt).

**2. Frage q08 hat einen neuen Wortlaut**

In `/var/www/investtimer/volafly-api/investtimer_fragen.json` heißt die Frage
jetzt „Wie unruhig ist der Anleihemarkt aktuell (MOVE)?“ (`quelle: neu`,
`ersetzt: q08`). Die InvestTimer-Vorlage für q08 auf diesen Wortlaut
umhängen. Im Vorlagentext den Halbsatz „aktuelle Renditen nenne ich deshalb
nicht“ streichen; der Rest bleibt. Der alte Katalog-Wortlaut soll auf
InvestTimer nicht mehr über die Vorlage laufen.

**3. Chat-Endpunkt nur noch über investtimer.net**

Der Endpunkt ist auch unter `https://api.volafly.net/v1/investtimer/chat`
erreichbar. api.volafly.net läuft über den Cloudflare-Proxy; prüfe, ob nginx
dort als Client-IP die Cloudflare-Adresse sieht. Unabhängig vom Ergebnis:
Im nginx-Block von api.volafly.net den Pfad `/v1/investtimer/` mit `404`
beantworten (Sicherung der nginx-Datei, `nginx -t` vor dem Reload).
`/v1/marktstress` bleibt dort erreichbar, InvestTimer ruft es über diese
Adresse ab.

**Tests nachher**

- `curl -s http://127.0.0.1:8100/v1/investtimer/chat` → `{"ok":true}`
- `curl -s https://investtimer.net/api/chat` → `{"ok":true}`
- `curl -s -o /dev/null -w "%{http_code}" https://api.volafly.net/v1/investtimer/chat` → `404`
- `curl -s https://api.volafly.net/v1/marktstress` → JSON mit `rounded`
- Frage it01 → Antwort nennt die Stufe passend zum aktuellen Wert
- neue MOVE-Frage → Vorlage greift, kein Hinweis auf fehlende Renditen
- Volafly: `/chat` ohne Token 401, `/data` ohne Token 401, volafly.net-KI
  unverändert

Am Ende kurz berichten: geänderte Stellen, Testergebnisse, neuer Text von
it01 und der MOVE-Vorlage.
