#!/usr/bin/env python3
"""InvestTimer: berechnet den Marktstress serverseitig und schreibt stress.json.

Oeffentlich wird nur das Ergebnis (Wert, Anzahl, Anteile). Rohwerte und
Anker bleiben auf dem Server. Nur Standardbibliothek, kein pip noetig.

Konfiguration ueber Umgebungsvariablen (siehe /etc/investtimer.env):
  METRICS_CSV_URL  CSV mit Spalten Metric, Value            (Pflicht)
  CONFIG_CSV_URL   CSV mit Spalten name, lo, hi, weight     (optional)
  OUTPUT_PATH      Zieldatei, Standard /var/lib/investtimer/data/stress.json

Aufruf:  update_stress.py            schreibt die Datei
         update_stress.py --check    rechnet nur und zeigt das Ergebnis
"""
import csv
import io
import json
import math
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

# name, block, metric | (numerator, denominator, offset)
COMPONENTS = [
    ("VIX", "volatility", "VIX", None),
    ("VIX_VXV", "volatility", None, ("VIX", "VXV", 0.0)),
    ("VIX_VX1", "volatility", None, ("VIX", "VX1", 0.0)),
    ("VX1_VX2", "volatility", None, ("VX1", "VX2", 0.0)),
    ("VVIX", "volatility", "VVIX", None),
    ("BREADTH_5", "price", "S5FD_Above_5Day_MA", None),
    ("BREADTH_20", "price", "S5TW_Above_20Day_MA", None),
    ("BREADTH_50", "price", "S5FI_Above_50Day_MA", None),
    ("BREADTH_200", "price", "S5TH_Above_200Day_MA", None),
    ("SPX_200D", "price", None, ("SPX", "SPX_200D", -1.0)),
    ("MOVE", "positioning", "MOVE_Index", None),
    ("EPC", "positioning", "Equity_Put_Call_Ratio", None),
    ("TPC", "positioning", "Total_Put_Call_Ratio", None),
    ("FG", "positioning", "Fear_Greed_Index", None),
]
BLOCKS = ["volatility", "price", "positioning"]

# Spezifikation vom 15.11.2026: name -> (lo, hi, weight). Greift, wenn der
# Config-Reiter fehlt oder nicht zu den 14 Komponenten passt.
DEFAULT_CONFIG = {
    "VIX": (12, 45, 10), "VIX_VXV": (0.78, 1.25, 10), "VIX_VX1": (0.85, 1.20, 5),
    "VX1_VX2": (0.88, 1.10, 5), "VVIX": (80, 160, 10), "MOVE": (60, 160, 10),
    "EPC": (0.45, 1.15, 7), "TPC": (0.65, 1.40, 8), "FG": (90, 1, 5),
    "BREADTH_5": (92, 8, 5), "BREADTH_20": (90, 10, 5), "BREADTH_50": (88, 12, 5),
    "BREADTH_200": (85, 15, 5), "SPX_200D": (0.10, -0.15, 10),
}

NUMBER = re.compile(r"^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:e[+-]?\d+)?$", re.I)


def parse_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if not isinstance(value, str):
        return None
    text = value.strip().replace("−", "-")
    if not NUMBER.match(text):
        return None
    number = float(text.replace(",", "."))
    return number if math.isfinite(number) else None


def fetch_rows(url):
    request = urllib.request.Request(url, headers={"User-Agent": "investtimer/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def metrics_from_rows(rows):
    if not rows:
        raise ValueError("Metrik-Tabelle ist leer.")
    header = [h.strip() for h in rows[0]]
    if "Metric" not in header or "Value" not in header:
        raise ValueError("Spalten Metric und Value erwartet, gefunden: %s" % header[:6])
    name_col, value_col = header.index("Metric"), header.index("Value")
    metrics = {}
    for row in rows[1:]:
        if len(row) <= max(name_col, value_col) or not row[name_col].strip():
            continue
        metrics.setdefault(row[name_col].strip(), parse_number(row[value_col]))
    return metrics


def validate_config(config):
    names = {c[0] for c in COMPONENTS}
    if set(config) != names:
        raise ValueError("Config passt nicht zu den 14 Komponenten.")
    total = 0.0
    for name, (lo, hi, weight) in config.items():
        if lo is None or hi is None or lo == hi:
            raise ValueError("Ungueltige Anker: " + name)
        if weight is None or weight <= 0 or weight > 10:
            raise ValueError("Ungueltiges Gewicht: " + name)
        if name.startswith("BREADTH_") and weight != 5:
            raise ValueError("Marktbreite muss Gewicht 5 haben.")
        total += weight
    if abs(total - 100) > 1e-9:
        raise ValueError("Gewichte ergeben nicht 100.")


def config_from_rows(rows):
    header = [h.strip() for h in rows[0]] if rows else []
    cols = [header.index(h) if h in header else -1 for h in ("name", "lo", "hi", "weight")]
    if min(cols) < 0:
        raise ValueError("Spalten name, lo, hi, weight erwartet.")
    config = {}
    for row in rows[1:]:
        if len(row) <= max(cols) or not row[cols[0]].strip():
            continue
        name = row[cols[0]].strip()
        if name in config:
            raise ValueError("Doppelte Komponente: " + name)
        config[name] = tuple(parse_number(row[c]) for c in cols[1:])
    validate_config(config)
    return config


def raw_value(metrics, metric, ratio):
    if metric:
        return metrics.get(metric)
    numerator, denominator, offset = ratio
    n, d = metrics.get(numerator), metrics.get(denominator)
    if n is None or d is None or d <= 0:
        return None
    return n / d + offset


def js_round(x):
    """Wie Math.round in JavaScript (halbe Werte aufrunden)."""
    return int(math.floor(x + 0.5))


def calculate(metrics, config):
    validate_config(config)
    rows = []
    for name, block, metric, ratio in COMPONENTS:
        lo, hi, weight = config[name]
        raw = raw_value(metrics, metric, ratio)
        score = None if raw is None else min(100.0, max(0.0, (raw - lo) / (hi - lo) * 100))
        rows.append({"name": name, "block": block, "weight": weight, "score": score})
    included = [r for r in rows if r["score"] is not None]
    weight_sum = sum(r["weight"] for r in included)
    exact = sum(r["weight"] * r["score"] for r in included) / weight_sum if weight_sum > 0 else None

    def share(weight):
        return round(weight / weight_sum * 100, 4) if weight_sum > 0 else 0

    return {
        "exact": exact,
        "rounded": None if exact is None else js_round(exact),
        "count": len(included),
        "total": len(rows),
        "rows": [{"name": r["name"], "effectiveWeight": share(r["weight"]) if r["score"] is not None else 0}
                 for r in rows],
        "blocks": [{"name": b, "effectiveWeight": share(sum(r["weight"] for r in included if r["block"] == b))}
                   for b in BLOCKS],
        "missing": [r["name"] for r in rows if r["score"] is None],
    }


def public_payload(result, now=None):
    now = now or datetime.now(timezone.utc)
    return {
        "model": "investtimer-us-market-stress",
        "asOf": now.astimezone().strftime("%Y-%m-%d"),
        "updatedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rounded": result["rounded"],
        "count": result["count"],
        "total": result["total"],
        "rows": result["rows"],
        "blocks": result["blocks"],
    }


def write_atomic(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(payload, out, ensure_ascii=False, separators=(",", ":"))
    os.chmod(temp, 0o644)
    os.replace(temp, path)


def main(argv):
    check = "--check" in argv
    metrics_url = os.environ.get("METRICS_CSV_URL", "").strip()
    config_url = os.environ.get("CONFIG_CSV_URL", "").strip()
    output = os.environ.get("OUTPUT_PATH", "/var/lib/investtimer/data/stress.json")
    if not metrics_url:
        print("FEHLER: METRICS_CSV_URL ist nicht gesetzt (/etc/investtimer.env).", file=sys.stderr)
        return 2
    metrics = metrics_from_rows(fetch_rows(metrics_url))
    config, config_source = DEFAULT_CONFIG, "eingebaute Standardwerte"
    if config_url:
        try:
            config, config_source = config_from_rows(fetch_rows(config_url)), "Config-Reiter"
        except Exception as error:  # Reiter fehlt oder passt nicht: Standard nutzen
            print("WARNUNG: Config-Reiter nicht nutzbar (%s), nutze Standardwerte." % error, file=sys.stderr)
    result = calculate(metrics, config)
    if result["rounded"] is None:
        print("FEHLER: Kein einziger Bestandteil verfuegbar, Datei bleibt unveraendert.", file=sys.stderr)
        return 1
    print("Marktstress %d (%d von %d Bestandteilen, Config: %s)%s" % (
        result["rounded"], result["count"], result["total"], config_source,
        "; fehlend: " + ", ".join(result["missing"]) if result["missing"] else ""))
    if not check:
        write_atomic(output, public_payload(result))
        print("geschrieben: " + output)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as error:
        print("FEHLER: %s" % error, file=sys.stderr)
        sys.exit(1)
