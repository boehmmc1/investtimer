#!/usr/bin/env python3
"""Mobil-Pruefung der ausgelieferten Seite (public/index.html).

Seit v1.2 prueft tools/check_v12.py die aktuelle Seite (Anmeldung, Kontomenue, Alarme, Film,
DE/EN, 320 bis 1280 px). Dieser Aufruf leitet dorthin weiter, damit der bekannte Befehl gilt.
Die alte Pruefung fuer die Seite bis v1.1 liegt in tools/check_mobile_v1.py.
"""
import os
import runpy
import sys

sys.exit(runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_v12.py"), run_name="__main__") or 0)
