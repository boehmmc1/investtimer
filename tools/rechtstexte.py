#!/usr/bin/env python3
"""Baut Impressum und Datenschutzerklaerung aus docs/rechtstexte/ nach public/.

Aufruf: python3 tools/rechtstexte.py [--entwurf zielordner]

Ohne --entwurf: bricht ab, solange ein <mark> (offene Stelle) im Text steht.
Sobald beide Seiten in public/ liegen, blendet build_v12.py Registrieren und
Anmelden ein und verlinkt die Seiten im Fuss. Danach die Seite neu bauen.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUELLE = ROOT / "docs" / "rechtstexte"
SEITEN = {"impressum": "Impressum", "datenschutz": "Datenschutzerklärung"}


def main():
    entwurf = "--entwurf" in sys.argv
    ziel = Path(sys.argv[sys.argv.index("--entwurf") + 1]) if entwurf else ROOT / "public"
    kopf, fuss = (QUELLE / "_kopf.html").read_text(encoding="utf-8"), (QUELLE / "_fuss.html").read_text(encoding="utf-8")
    for name, titel in SEITEN.items():
        text = (QUELLE / (name + ".body.html")).read_text(encoding="utf-8")
        if not entwurf and "<mark>" in text:
            raise SystemExit("%s: noch %d offene Stellen (<mark>), nicht veroeffentlicht" % (name, text.count("<mark>")))
        if not entwurf:
            text = text.replace("<!-- ", "<!--").split("\n")
            text = "\n".join(z for z in text if not z.startswith("<!--"))
        ziel.mkdir(parents=True, exist_ok=True)
        (ziel / (name + ".html")).write_text(kopf.replace("__TITEL__", titel) + text + fuss, encoding="utf-8")
        print("geschrieben:", ziel / (name + ".html"))


if __name__ == "__main__":
    main()
