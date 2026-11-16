#!/usr/bin/env python3
"""InvestTimer: holt den Marktstress von der Volafly-API und legt ihn als
stress.json fuer die Seite ab. Keine eigene Berechnung, keine Rohdaten.

Umgebungsvariablen (siehe /etc/investtimer.env):
  STRESS_API_URL     Standard https://api.volafly.net/v1/marktstress
  OUTPUT_PATH        Standard /var/lib/investtimer/data/stress.json
  PUBLIC_DELAY_DAYS  Standard 7

Zusaetzlich fuehrt das Skript einen Tagesverlauf (history.json neben der
Ausgabedatei, nicht oeffentlich ausgeliefert) und legt in stress.json unter
"publicSnapshot" den Stand bei, der mindestens PUBLIC_DELAY_DAYS alt ist. Gibt
es noch keinen so alten Stand, ist es der aelteste vorhandene, mit echtem Datum.

Aufruf:  update_stress.py            schreibt die Datei
         update_stress.py --check    ruft nur ab und zeigt das Ergebnis
Bei jedem Fehler bleibt die vorhandene Datei unveraendert.
"""
import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import date, timedelta

DEFAULT_URL = "https://api.volafly.net/v1/marktstress"
PUBLIC_KEYS = ("model", "asOf", "updatedAt", "rounded", "count", "total", "rows", "blocks")


def validate(data):
    """Nur die erwartete Form durchlassen; alles andere wird verworfen."""
    if not isinstance(data, dict):
        raise ValueError("Antwort ist kein JSON-Objekt.")
    rounded = data.get("rounded")
    if not (isinstance(rounded, int) and not isinstance(rounded, bool) and 0 <= rounded <= 100):
        raise ValueError("rounded fehlt oder liegt nicht zwischen 0 und 100.")
    if not isinstance(data.get("count"), int):
        raise ValueError("count fehlt.")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(data.get("asOf", ""))):
        raise ValueError("asOf fehlt (JJJJ-MM-TT).")
    for key in ("rows", "blocks"):
        parts = data.get(key)
        if not isinstance(parts, list) or not parts:
            raise ValueError(key + " fehlt.")
        for part in parts:
            if not (isinstance(part, dict) and isinstance(part.get("name"), str)
                    and isinstance(part.get("effectiveWeight"), (int, float))):
                raise ValueError(key + " hat eine unerwartete Form.")
    clean = {k: data[k] for k in PUBLIC_KEYS if k in data}
    clean["rows"] = [{"name": p["name"], "effectiveWeight": p["effectiveWeight"]} for p in data["rows"]]
    clean["blocks"] = [{"name": p["name"], "effectiveWeight": p["effectiveWeight"]} for p in data["blocks"]]
    return clean


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "investtimer/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def write_atomic(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(payload, out, ensure_ascii=False, separators=(",", ":"))
    os.chmod(temp, 0o644)
    os.replace(temp, path)


def load_history(path, seed_path):
    for candidate in (path, seed_path):
        try:
            with open(candidate, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and data:
                return {day: entry for day, entry in data.items() if re.match(r"^\d{4}-\d{2}-\d{2}$", day)}
        except (OSError, ValueError):
            continue
    return {}


def public_snapshot(history, today, delay_days):
    """Juengster Stand, der mindestens delay_days alt ist; sonst der aelteste."""
    if not history:
        return None
    limit = (date.fromisoformat(today) - timedelta(days=delay_days)).isoformat()
    old_enough = [day for day in history if day <= limit]
    day = max(old_enough) if old_enough else min(history)
    return history[day]


def main(argv):
    url = os.environ.get("STRESS_API_URL", "").strip() or DEFAULT_URL
    output = os.environ.get("OUTPUT_PATH", "").strip() or "/var/lib/investtimer/data/stress.json"
    payload = validate(fetch(url))
    print("Marktstress %d (%d von %s Bestandteilen, Datenstand %s)" % (
        payload["rounded"], payload["count"], payload.get("total", 14), payload["asOf"]))
    delay = int(os.environ.get("PUBLIC_DELAY_DAYS", "").strip() or 7)
    history_path = os.path.join(os.path.dirname(output), "history.json")
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_history.json")
    history = load_history(history_path, seed_path)
    history[payload["asOf"]] = {k: payload[k] for k in PUBLIC_KEYS if k in payload and k != "updatedAt"}
    history = dict(sorted(history.items())[-400:])
    snapshot = public_snapshot(history, payload["asOf"], delay)
    payload["publicSnapshot"] = snapshot
    print("oeffentlicher Stand: %s vom %s (Verzoegerung %d Tage, %d Tage im Verlauf)" % (
        snapshot["rounded"], snapshot["asOf"], delay, len(history)))
    if "--check" not in argv:
        write_atomic(history_path, history)
        os.chmod(history_path, 0o600)
        write_atomic(output, payload)
        print("geschrieben: " + output)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as error:
        print("FEHLER: %s" % error, file=sys.stderr)
        sys.exit(1)
