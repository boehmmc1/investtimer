#!/usr/bin/env python3
"""Analyse fuer den Text "So entsteht der Wert" (Nachtrag 2, nur intern, nichts davon wird angezeigt).

Wie stark verlief der Marktstress gegenlaeufig zum US-Aktienmarkt? Je Bestandteil, fuer den Gesamtwert (heutige Gewichte)
und fuer einfache Alternativen (gleichgewichtet, nur Kursschwankungen). Wochenschluss (Freitag), Tage mit >= 8 Bestandteilen
(wie die Seite). Kennzahlen (Pearson):
  r_ret   : Wochenaenderung des Werts vs. Wochenrendite des Gesamtmarkts (gegenlaeufig = negativ)
  r_dd    : Wertniveau vs. Abstand des Gesamtmarkts zum 52-Wochen-Hoch in % (gegenlaeufig = negativ: tiefer unter dem Hoch, hoeher der Wert)
  treffer : Anteil der Wochen mit >10 % Abstand zum Hoch, in denen der Wert >= 60 lag
Aufruf: python3 historie/analyse_narrativ.py <ausgabe.json>   (liest nur /var/lib/investtimer/historie)
"""
import json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rechnen as rc  # gleiche Datenaufbereitung wie die Rueckrechnung
ms = rc.ms

def main(ziel):
    config = {k: tuple(v) for k, v in json.load(open(os.path.join(rc.HIER, "config.json")))["config"].items()}
    serien = {m: rc.lade(k) for m, k in rc.SERIEN.items()}
    spx = serien["SPX"]; serien["SPX_200D"] = spx.rolling(200, min_periods=200).mean()
    tage = pd.DataFrame(serien).sort_index()
    tage = tage[tage.index >= "2006-10-01"]
    # Teilwerte je Bestandteil (0-100), wie marktstress.calculate
    teil = {}
    for name, block, metrik, ratio in ms.COMPONENTS:
        def wert(z, metrik=metrik, ratio=ratio):
            w = {k: (None if pd.isna(v) else float(v)) for k, v in z.items()}
            return ms.raw_value(w, metrik, ratio)
        roh = tage.apply(lambda z: wert(z), axis=1)
        lo, hi, _ = config[name]
        teil[name] = ((roh.astype(float) - lo) / (hi - lo) * 100).clip(0, 100)
    T = pd.DataFrame(teil)
    anz = T.notna().sum(axis=1)
    T = T[anz >= 8]
    gew = {n: config[n][2] for n in T.columns}
    blk = {name: block for name, block, _, _ in ms.COMPONENTS}
    def gewichtet(g):
        w = pd.Series(g)
        return (T.mul(w, axis=1)).sum(axis=1) / T.notna().mul(w, axis=1).sum(axis=1)
    varianten = {"heute (Gewichte Stress_Config)": gewichtet(gew), "gleichgewichtet": gewichtet({n: 1 for n in T.columns}),
                 "nur Kursschwankungen": gewichtet({n: (gew[n] if blk[n] == "volatility" else 0) for n in T.columns})}
    markt = spx.reindex(T.index).ffill()
    woche = lambda s: s.resample("W-FRI").last()
    mw = woche(markt); ret = mw.pct_change() * 100
    hoch = markt.rolling(252, min_periods=60).max(); dd = woche((markt / hoch - 1) * 100)
    zeitraeume = {"2006-2026": ("2006-10-01", "2026-12-31"), "2006-2015": ("2006-10-01", "2015-12-31"),
                  "2016-2026": ("2016-01-01", "2026-12-31"), "letzte 5 Jahre": ("2021-11-01", "2026-12-31")}
    def kennzahlen(s):
        sw = woche(s); aus = {}
        for zn, (a, b) in zeitraeume.items():
            m = (sw.index >= a) & (sw.index <= b)
            d = pd.DataFrame({"s": sw[m], "ds": sw.diff()[m], "ret": ret[m], "dd": dd[m]}).dropna()
            tief = d[d["dd"] < -10]
            aus[zn] = {"r_ret": round(d["ds"].corr(d["ret"]), 3), "r_dd": round(d["s"].corr(d["dd"]), 3), "wochen": int(len(d)),
                       "treffer_bei_10proz_abstand": round(float((tief["s"] >= 60).mean()), 3) if len(tief) else None, "wochen_10proz_abstand": int(len(tief))}
        return aus
    erg = {"varianten": {k: kennzahlen(v) for k, v in varianten.items()},
           "bestandteile": {n: kennzahlen(T[n]) for n in T.columns},
           "hinweis": "Pearson-Korrelationen auf Wochenbasis; Rueckrechnung mit dem heutigen Modell, daher in-sample. Keine Aussage ueber die Zukunft."}
    json.dump(erg, open(ziel, "w"), ensure_ascii=False, indent=1)
    for k, v in erg["varianten"].items():
        print("%-32s" % k, {z: (x["r_ret"], x["r_dd"], x["treffer_bei_10proz_abstand"]) for z, x in v.items()})
    print("Bestandteile (2006-2026: r_ret, r_dd):")
    for n, v in sorted(erg["bestandteile"].items(), key=lambda kv: kv[1]["2006-2026"]["r_dd"]):
        print("  %-12s %s" % (n, (v["2006-2026"]["r_ret"], v["2006-2026"]["r_dd"], v["2006-2026"]["wochen"])))

if __name__ == "__main__":
    main(sys.argv[1])
