#!/usr/bin/env python3
"""Pruefung der ausgelieferten Seite (public/index.html) vor jedem Push.

Laeuft die UI-Tests unter tests/ui/ gegen public/ mit nachgespielter API (tests/ui/harness.py):
Navigation, Safe-Area, Verlauf, Stufen, KI-Bereich und KI-Bruecke, Start ohne Zwischenwert, Updates/Offline,
Zustaende, und die Gesamtpruefung (--schnell: 320/390/1280; --voll: 9 Groessen). Endet mit 1 bei Auffaelligkeiten.
Braucht playwright und Chrome (Python mit playwright aufrufen, z. B. die Testumgebung im Scratchpad).
Die alte Pruefung (Chat-Dialog der v1.2-Seite) liegt in tools/check_v12.py.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
UI = Path(__file__).resolve().parent.parent / 'tests' / 'ui'
TESTS = ['test_navigation.py', 'test_safearea.py', 'test_verlauf.py', 'test_stufen.py', 'test_ki.py', 'test_start.py', 'test_zustaende.py', 'test_update.py', 'test_feedback.py', 'test_rueckkehr.py', 'test_block11.py', 'test_ki_limit.py', 'test_teilen.py']
fehler = 0
for t in TESTS:
    r = subprocess.run([sys.executable, str(UI / t)], capture_output=True, text=True)
    zeilen = [z for z in r.stdout.splitlines() if z.startswith('FEHL ')]
    print(('ok   ' if r.returncode == 0 else 'FEHL ') + t + ('' if r.returncode == 0 else ': ' + '; '.join(zeilen[:5]) + (r.stderr.strip().splitlines() or [''])[-1]))
    fehler += r.returncode != 0
with tempfile.NamedTemporaryFile(suffix='.json') as f:
    r = subprocess.run([sys.executable, str(UI / 'test_gesamt.py'), f.name] + ([] if '--voll' in sys.argv else ['--schnell']), capture_output=True, text=True)
    befunde = json.load(open(f.name)) if Path(f.name).stat().st_size else [{'befund': 'Gesamtpruefung abgebrochen', 'ansicht': '-'}]
# Erwartet: das geoeffnete Kontomenue liegt als Aufklappmenue ueber dem Inhalt
echt = [b for b in befunde if b['ansicht'] != 'Kontomenue']
print(('ok   ' if not echt else 'FEHL ') + 'Gesamtpruefung: %d Befunde' % len(echt))
for b in echt[:15]:
    print('     [%s] %s (%s %s %s)' % (b['ansicht'], b['befund'], b.get('groesse'), b.get('zustand'), b.get('sprache')))
fehler += bool(echt)
print('SUMME', 'keine Auffaelligkeiten' if not fehler else '%d Pruefungen mit Befund' % fehler)
sys.exit(1 if fehler else 0)
