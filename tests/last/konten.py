#!/usr/bin/env python3
"""Testkonten fuer den Lasttest: konten.py anlegen <n> | loeschen. Tokens/IDs in /var/lib/investtimer/last/konten.json (0600)."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "qa"))
os.environ.setdefault("QA_AUSGABE", "/var/lib/investtimer/last")
import gemeinsam as g
DATEI = Path("/var/lib/investtimer/last/konten.json")
if sys.argv[1] == "anlegen":
    k = [g.testkonto() for _ in range(int(sys.argv[2]))]
    g._angelegt.clear()
    DATEI.write_text(json.dumps([{"id": x["id"], "token": x["token"]} for x in k])); os.chmod(DATEI, 0o600)
    print(len(k), "Testkonten angelegt")
else:
    k = json.loads(DATEI.read_text())
    for x in k:
        g.testkonto_weg(x["id"])
    DATEI.unlink(); print(len(k), "Testkonten geloescht")
