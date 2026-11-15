"""Marktstress-Rechenkern fuer die Volafly-API (Endpunkt GET /v1/marktstress).

Reine Standardbibliothek, keine Netzwerkzugriffe: Die API reicht die Zeilen
herein, die sie ohnehin schon liest, und gibt nur das Ergebnis heraus
(Wert, Anzahl, Anteile). Rohwerte und Anker verlassen die API nicht.

Einziger Einstieg fuer die API:
    payload = marktstress.payload_from_rows(metric_rows, config_rows)
      metric_rows  Zeilen des Haupt-Reiters (Kopfzeile mit Metric, Value)
      config_rows  Zeilen des Reiters Stress_Config (name, lo, hi, weight);
                   None oder unpassend -> eingebaute Standardwerte
    Ergebnis: dict fuer die JSON-Antwort. Wirft ValueError, wenn kein
    einziger Bestandteil berechenbar ist.
"""
import math
import re
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


def metrics_from_rows(rows):
    if not rows:
        raise ValueError("Metrik-Tabelle ist leer.")
    header = [str(h).strip() for h in rows[0]]
    if "Metric" not in header or "Value" not in header:
        raise ValueError("Spalten Metric und Value erwartet, gefunden: %s" % header[:6])
    name_col, value_col = header.index("Metric"), header.index("Value")
    metrics = {}
    for row in rows[1:]:
        if len(row) <= name_col or not str(row[name_col]).strip():
            continue
        value = row[value_col] if len(row) > value_col else None
        metrics.setdefault(str(row[name_col]).strip(), parse_number(value))
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
    header = [str(h).strip() for h in rows[0]] if rows else []
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


def payload_from_rows(metric_rows, config_rows=None):
    """Zeilen rein, oeffentliche Antwort raus. Einstieg fuer die API."""
    metrics = metrics_from_rows([[("" if c is None else c) if not isinstance(c, (int, float)) else c
                                  for c in row] for row in metric_rows])
    config = DEFAULT_CONFIG
    if config_rows:
        try:
            config = config_from_rows([["" if c is None else str(c) for c in row] for row in config_rows])
        except Exception:
            config = DEFAULT_CONFIG
    result = calculate(metrics, config)
    if result["rounded"] is None:
        raise ValueError("Kein Bestandteil verfuegbar.")
    return public_payload(result)
