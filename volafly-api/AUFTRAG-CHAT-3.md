# Auftrag: Einstiegsfragen der v1.2-Seite auf den Sparpfad legen

Auftragstext für Claude Code auf dem Server (Ordner `/root/volafly-chat`).
Sicherung vorher, Tests nachher, bei Fehlschlag zurückspielen. `/chat`
(Volafly) bleibt unverändert.

---

Die neue Seite (v1.2, derzeit unter https://investtimer.net/neu/) stellt im
KI-Einstieg zwei eigene Fragen. Sie laufen bisher über den freien Chat und
kosten jedes Mal einen Modellaufruf. Lege sie als Aliase auf vorhandene
InvestTimer-Einträge:

| Frage der Seite | Alias für |
|---|---|
| „Warum steht der Marktstress bei 36?“ – die Zahl ist der jeweils angezeigte Wert, also jede ganze Zahl von 0 bis 100 | it01 (aktueller Stand und Treiber) |
| „Wie setzt sich der Wert zusammen?“ | it02 (Entstehung aus 14 Bestandteilen) |

Die Antwort auf die erste Frage nennt immer den aktuellen Wert aus dem
Live-Werkzeug, nicht die Zahl aus der Frage.

**Tests nachher**

- beide Fragen über `http://127.0.0.1:8100/v1/investtimer/chat` → Vorlage bzw.
  fertige Antwort greift (kein freier Modellaufruf im `[usage]`-Log für it02)
- „Warum steht der Marktstress bei 12?“ → Antwort nennt den aktuellen Wert
- eine bisherige Katalogfrage → unverändert
- Volafly: `/chat` ohne Token 401

Am Ende kurz berichten: geänderte Stellen und Testergebnisse.
