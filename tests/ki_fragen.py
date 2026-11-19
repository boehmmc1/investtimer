#!/usr/bin/env python3
"""Stellt die Pruef-Fragen an die KI-Testinstanz (tests/ki_instanz.sh, Port 8198) und prueft den Stil.
Aufruf: tests/ki_fragen.py <ausgabe.json> [wert]"""
import json, re, sys, time, urllib.request
WERT = sys.argv[2] if len(sys.argv) > 2 else '46'
FRAGEN = ["Was bedeutet der heutige Wert?", "Was misst InvestTimer eigentlich?", "Woraus setzt sich der Wert zusammen?",
          "Ist %s viel oder wenig?" % WERT, "Was bewegt den Wert gerade?", "Wie nervös ist der Markt im Moment?",
          "Wann war der Marktstress zuletzt so hoch?", "Wie sah es im Corona-Crash 2020 aus?", "Wie lange dauern Stressphasen meistens?",
          "Warum steht der Marktstress bei %s?" % WERT]
ZUSATZ = ["Soll ich jetzt verkaufen?", "Wie stark ist welcher Blickwinkel gewichtet?"]
VERBOTEN = ["Es ist wichtig zu beachten", "spielt eine entscheidende Rolle", "stand ganz im Zeichen", "Zusammenfassend", "letztlich",
            "grundsätzlich", "VIX", "VVIX", "VXV", "MOVE", "Put/Call", "Put-Call", "S&P", "Terminkurve", "Prozent", "%", "**", "\n- ", "\n#"]
def frage(f, i):
    req = urllib.request.Request('http://127.0.0.1:8198/v1/investtimer/chat', data=json.dumps({'frage': f, 'verlauf': [], 'sprache': 'de'}).encode(),
                                 headers={'Content-Type': 'application/json', 'X-Real-IP': '10.99.%d.%d' % (int(time.time()) % 200, i)})
    t = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=180))
    return d.get('antwort', ''), round(time.time() - t, 1), bool(d.get('belege'))
def pruefung(f, a):
    w = len(a.split()); verlauf = any(k in f for k in ('Corona', 'zuletzt', 'Stressphasen', 'Wochen'))
    m = []
    if not (60 <= w <= (180 if verlauf else 140)): m.append('Länge %d Wörter' % w)
    for v in VERBOTEN:
        if v in a: m.append('enthält "%s"' % v.strip())
    if re.search(r'(?m)^Mit ', a) or re.search(r'[.!?] Mit ', a): m.append('Satzanfang "Mit"')
    if re.search(r'weniger\b[^.]{0,80}\bals vielmehr', a): m.append('"weniger … als vielmehr"')
    if 'Anlageberatung' in a and not any(k in f for k in ('kaufen', 'verkaufen')): m.append('"Keine Anlageberatung" ohne Kauf-/Verkaufsfrage')
    return w, m
aus = []
for i, f in enumerate(FRAGEN + ZUSATZ):
    a, s, b = frage(f, i)
    w, m = pruefung(f, a)
    aus.append({'frage': f, 'antwort': a, 'woerter': w, 'sekunden': s, 'belege': b, 'maengel': m, 'zusatz': f in ZUSATZ})
    print('%-48s %3d W  %s' % (f[:48], w, '; '.join(m) or 'ok'), flush=True)
json.dump(aus, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
