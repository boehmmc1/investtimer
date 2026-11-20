#!/usr/bin/env python3
"""Fasst ergebnisse.jsonl eines QA-Laufs zusammen: Ampel je Bereich (rot: kritischer/hoher Befund, gelb: mittlerer/niedriger,
gruen: nur bestanden/Hinweise), Befundliste. Aufruf: bericht.py <ordner> [--mail] -> kurzbericht.md (und Mail an info@investtimer.net)."""
import collections
import json
import os
import sys
import urllib.request
from pathlib import Path

ordner = Path(sys.argv[1])
zeilen = [json.loads(z) for z in (ordner / "ergebnisse.jsonl").read_text().splitlines() if z.strip()]
BEREICHE = ["1 Funktion", "2 Daten", "3 Sicherheit", "4 Datenschutz", "5 Qualitaet", "6 Betrieb"]
RANG = {"kritisch": 3, "hoch": 3, "mittel": 2, "niedrig": 2}
je = collections.defaultdict(list)
for z in zeilen:
    je[z["bereich"]].append(z)
aus = ["# InvestTimer QA-Kurzbericht · %s" % ordner.name, ""]
gesamt = 0
for b in BEREICHE:
    e = je.get(b, [])
    if not e:
        aus.append("- **%s**: nicht gelaufen" % b)
        continue
    befunde = [z for z in e if not z["ok"] and z["schwere"] != "info"]
    stufe = max([RANG.get(z["schwere"], 0) for z in befunde] or [0])
    gesamt = max(gesamt, stufe)
    ampel = {0: "grün", 2: "gelb", 3: "rot"}[stufe]
    aus.append("- **%s**: %s – %d bestanden, %d Befunde, %d Hinweise" % (b, ampel, sum(z["ok"] for z in e), len(befunde),
                                                                         sum(1 for z in e if not z["ok"] and z["schwere"] == "info")))
aus += ["", "## Befunde", ""]
for z in sorted(zeilen, key=lambda z: (-RANG.get(z["schwere"], 0), z["bereich"])):
    if not z["ok"] and z["schwere"] != "info":
        aus.append("- [%s] %s · %s%s" % (z["schwere"], z["bereich"], z["name"], (" → " + z["info"][:200]) if z["info"] else ""))
aus += ["", "## Hinweise", ""] + ["- %s · %s" % (z["bereich"], z["name"]) for z in zeilen if not z["ok"] and z["schwere"] == "info"]
text = "\n".join(aus) + "\n"
(ordner / "kurzbericht.md").write_text(text)
print(text)
if "--mail" in sys.argv:
    key = open("/root/.investtimer/resend-key").read().strip()
    ampel = {0: "grün", 2: "gelb", 3: "rot"}[gesamt]
    req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "investtimer-qa"},
                                 data=json.dumps({"from": "InvestTimer QA <alarm@investtimer.net>", "to": [os.environ.get("QA_MAIL_AN", "info@investtimer.net")],
                                                  "subject": "%sInvestTimer QA-Kurzbericht – %s (%s)" % (os.environ.get("QA_BETREFF_PRAEFIX", ""), ordner.name, ampel),
                                                  "text": text}).encode())
    print("Mail:", json.load(urllib.request.urlopen(req, timeout=20)).get("id"))
