#!/usr/bin/env python3
"""Tageskurse (Schluss) der 14 Marktstress-Bestandteile und des S&P 500 fuer die Rueckrechnung.

Bezugsweg wie beim Live-Scraper (TradingView-Websocket, dieselben Symbole; Fear & Greed von CNN).
Nur lesend. Ergebnis: historie/daten/<KEY>.csv (date, close). Aufruf: python3 historie/holen.py [KEY ...]
"""
import csv, os, sys
sys.path.insert(0, "/root/volafly-video")
from fetch_history import fetch  # noqa: E402  (gleicher Websocket-Abruf wie fuer den Erklaerfilm)

SYMBOLS = {
    "VIX": "TVC:VIX", "VXV": "CBOE:VIX3M", "VX1": "CBOE:VX1!", "VX2": "CBOE:VX2!",
    "VVIX": "CBOE:VVIX", "MOVE": "TVC:MOVE", "EPC": "USI:PCCE", "TPC": "USI:PCC",
    "B5": "INDEX:S5FD", "B20": "INDEX:S5TW", "B50": "INDEX:S5FI", "B200": "INDEX:S5TH",
    "SPX": "TVC:SPX",
}
OUT = os.environ.get("IT_HISTORIE_DATEN", "/var/lib/investtimer/historie/daten")  # Rohdaten nicht ins (oeffentliche) Repo


def speichern(key, bars):
    with open(os.path.join(OUT, key + ".csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "close"])
        for d in sorted(bars):
            w.writerow([d.isoformat(), bars[d]])


def fear_greed():
    """CNN Fear & Greed, Tageswerte ab 15.07.2020 (frueher liefert CNN nichts)."""
    import requests
    from datetime import datetime, timezone
    h = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
         "Accept": "application/json", "Referer": "https://edition.cnn.com/", "Origin": "https://edition.cnn.com"}
    r = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2020-07-15", headers=h, timeout=30)
    r.raise_for_status()
    return {datetime.fromtimestamp(p["x"] / 1000, tz=timezone.utc).date(): float(p["y"]) for p in r.json()["fear_and_greed_historical"]["data"]}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) == 1 or "FG" in sys.argv[1:]:
        try:
            fg = fear_greed(); speichern("FG", fg); ds = sorted(fg)
            print("FG    CNN          %5d Tage  %s .. %s" % (len(ds), ds[0], ds[-1]), flush=True)
        except Exception as e:
            print("FG    CNN          FEHLER %s" % e)
    for key, symbol in SYMBOLS.items():
        if len(sys.argv) > 1 and key not in sys.argv[1:]:
            continue
        try:
            bars = fetch(symbol, n=12000)
        except Exception as e:
            print("%-5s %-12s FEHLER %s" % (key, symbol, e)); continue
        speichern(key, bars)
        ds = sorted(bars)
        print("%-5s %-12s %5d Tage  %s .. %s" % (key, symbol, len(ds), ds[0] if ds else "-", ds[-1] if ds else "-"), flush=True)
