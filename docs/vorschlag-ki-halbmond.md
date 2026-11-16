# Vorschlag: KI-Bot im Halbmond (Branch `feature/ki-halbmond`)

## Leitidee

Der Halbmond ist bisher nur das Logo und der Signalbogen. Der Vorschlag macht ihn zum
Zeichen des KI-Bots. Die rotierende Netzkugel stammt aus dem Volafly-Look und läuft dauerhaft
per Canvas; sie entfällt.

| Stelle | Vorher | Nachher |
|---|---|---|
| Signalbogen | statisch gezeichnet | füllt sich beim Laden von 0 auf den Wert; die Zahl zählt mit (300 ms Halt, 1,5 s); neue Live-Werte gleiten (0,7 s); Marken bei 25/50/75 für die vier Stufen |
| Einstieg in den Chat | Textlink „Frage stellen“ | Knopf „Was treibt die 35? KI fragen“ direkt unter dem Wert; ein Tipp stellt die Frage sofort |
| Kopf des KI-Bereichs | Netzkugel, zwei Überzeilen | Halbmond-Zeichen, gefüllt bis zum aktuellen Wert, eine Überschrift mit einem erklärenden Satz |
| Antworten | Kasten ohne Absender | kleiner Halbmond als Absender; während eine Antwort entsteht, wandert ein Segment über ihn (Denk-Anzeige) |
| Musterfragen | drei Karten in einer Karte | drei Spalten ohne eigene Kartenfläche |
| Handy / App | Chat im Seitenfluss | laufendes Gespräch als Vollbild, Eingabe unten in der Daumenzone, Schließen führt zurück |
| App-Grundlage | – | `manifest.json`, App-Icons (192, 512, maskable), App-Meta |

Bei reduzierter Bewegung steht der Wert sofort, die Ansichten erscheinen ohne Bewegung, und der
Text „InvestTimer liest die Daten …“ trägt den Denk-Zustand allein.

## Geprüft

- `tools/check_mobile.py`: keine Auffälligkeiten (6 Bildschirmgrößen).
- Bewegung mit Fake-Uhr bildgenau aufgenommen: Einstieg, Live-Wechsel, Zielwechsel mitten in der
  Füllung (stetig, gleiche Enddauer), Vollbild-Ansicht, Denk-Anzeige, Antwort-Einblendung; jeweils
  auch mit reduzierter Bewegung.

## Nächste Schritte für die App (nicht in diesem Branch)

1. Service Worker mit Offline-Hülle (letzter Wert bleibt sichtbar), Voraussetzung für Installierbarkeit
   in Chrome und für eine TWA.
2. App-Hülle: Android über Trusted Web Activity (Bubblewrap), iOS über Capacitor. Beide laden
   investtimer.net; das Manifest hier ist die gemeinsame Basis.
3. Im Chat nach jeder Antwort zwei passende Folgefragen aus `investtimer_fragen.json` anbieten.
4. Für die App eine native Teilen-Funktion für Antworten (Web Share API).
