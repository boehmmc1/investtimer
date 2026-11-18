#!/usr/bin/env python3
"""Rueckrechnung des Marktstress je Handelstag mit exakt der Live-Logik.

- Rechenkern: marktstress.calculate (derselbe wie in der API), Config aus historie/config.json
  (Stand des Sheet-Reiters Stress_Config; identisch mit den eingebauten Standardwerten).
- Je Tag nur Werte, die an genau diesem Handelstag vorliegen. Kein Vortragen, kein Schaetzen.
- Futures-Tageskerzen mit Sonntagsdatum gehoeren zum naechsten Boersentag (wie im Film-Backtest).
- SPX_200D = einfacher Durchschnitt der letzten 200 Schlusskurse (wie bei Barchart).
- Nur Tage VOR dem ersten aufgezeichneten Tag (aufgezeichnete Werte werden nie ersetzt).

Ausgabe: /var/lib/investtimer/historie/rueckrechnung.json (nur auf dem Server, nicht im Repo)  {"stand", "quelle", "tage": {datum: payload mit exact/count/rows/blocks}}
"""
import json, os, sys
import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/root/volafly-chat")
import marktstress as ms  # noqa: E402

DATEN = os.environ.get("IT_HISTORIE_DATEN", "/var/lib/investtimer/historie/daten")
ZIEL = os.environ.get("IT_RUECKRECHNUNG", "/var/lib/investtimer/historie/rueckrechnung.json")
AUFGEZEICHNET = os.environ.get("IT_HISTORY", "/var/lib/investtimer/data/history.json")
SERIEN = {"VIX": "VIX", "VXV": "VXV", "VX1": "VX1", "VX2": "VX2", "VVIX": "VVIX", "MOVE_Index": "MOVE",
          "Equity_Put_Call_Ratio": "EPC", "Total_Put_Call_Ratio": "TPC", "Fear_Greed_Index": "FG",
          "S5FD_Above_5Day_MA": "B5", "S5TW_Above_20Day_MA": "B20", "S5FI_Above_50Day_MA": "B50",
          "S5TH_Above_200Day_MA": "B200", "SPX": "SPX"}


def lade(key):
    pfad = os.path.join(DATEN, key + ".csv")
    if not os.path.exists(pfad):
        return pd.Series(dtype=float)
    s = pd.read_csv(pfad, parse_dates=["date"]).set_index("date")["close"].astype(float)
    if (s.index.dayofweek == 6).any():
        s.index = s.index + pd.offsets.BDay(1)
    return s[~s.index.duplicated(keep="last")].sort_index()


def bloecke(werte, config):
    """Teilwerte 0-100 der drei Blickwinkel (gleiche Formel wie marktstress.calculate, je Block gewichtet)."""
    summe = {}
    for name, block, metrik, ratio in ms.COMPONENTS:
        roh = ms.raw_value(werte, metrik, ratio)
        if roh is None:
            continue
        lo, hi, w = config[name]
        score = min(100.0, max(0.0, (roh - lo) / (hi - lo) * 100))
        a = summe.setdefault(block, [0.0, 0.0])
        a[0] += w * score; a[1] += w
    return {b: round(v[0] / v[1], 1) for b, v in summe.items() if v[1] > 0}


def main():
    config = {k: tuple(v) for k, v in json.load(open(os.path.join(HIER, "config.json")))["config"].items()}
    serien = {metrik: lade(key) for metrik, key in SERIEN.items()}
    spx = serien["SPX"]
    serien["SPX_200D"] = spx.rolling(200, min_periods=200).mean()
    try:
        erster = min(json.load(open(AUFGEZEICHNET)))
    except (OSError, ValueError):
        erster = "9999-12-31"
    tage = {}
    for d in spx.index:
        datum = d.date().isoformat()
        if datum >= erster:
            continue
        werte = {m: float(s[d]) for m, s in serien.items() if d in s.index and pd.notna(s[d])}
        r = ms.calculate(werte, config)
        if r["rounded"] is None:
            continue
        tage[datum] = {"asOf": datum, "exact": round(r["exact"], 3), "rounded": r["rounded"], "count": r["count"],
                       "total": r["total"], "rows": r["rows"], "blocks": r["blocks"], "missing": r["missing"],
                       "bloecke": bloecke(werte, config)}
    json.dump({"stand": pd.Timestamp.now().strftime("%Y-%m-%d"), "erster_aufgezeichnet": erster,
               "quelle": "TradingView-Tageskurse (Symbole wie Live-Scraper), Fear & Greed: CNN",
               "config": {k: list(v) for k, v in config.items()}, "tage": tage},
              open(ZIEL, "w"), separators=(",", ":"))
    n = [t["count"] for t in tage.values()]
    print("Tage:", len(tage), "| ab 8 Bestandteilen:", sum(1 for x in n if x >= 8), "| erster:", min(tage), "| letzter:", max(tage))


if __name__ == "__main__":
    main()
