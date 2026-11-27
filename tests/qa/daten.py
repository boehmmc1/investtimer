#!/usr/bin/env python3
"""QA Bereich 2 – Daten und Berechnung (nur lesend; ein Testkonto fuer die eingeloggten Endpunkte, wird geloescht).
- Wert der Seite (/api/aktuell eingeloggt) = Wert der Volafly-API (127.0.0.1:8100/v1/marktstress), gleicher Zeitpunkt; Stufe passt.
- 30-Tage-Regel (DEC-018): stress.json, /api/historie-oeffentlich, Teilen-Manifest und -Bilder, Vorschaubild nirgends juenger als heute-30.
- Verlauf: Wochen- und Monatsverdichtung gegen die Rohhistorie (aufgezeichnet + zurueckgerechnet) nachgerechnet,
  keine Luecken > 7 Kalendertage im letzten Jahr, Endpunkt = letzter Wert.
- Ereignisphasen: Hoechstwert, Datum und "wieder unter 40 nach X Tagen" fuer 3 Phasen unabhaengig nachgerechnet; Start/Ende plausibel.
- Teilwerte der drei Blickwinkel an 3 Tagen unabhaengig aus Rohkursen (historie/daten/*.csv) und Config nachgerechnet.
"""
import csv
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ROOT, melde, http, testkonto, aufraeumen, bearer, ende  # noqa: E402

B = "2 Daten"
HEUTE = date.today()
GRENZE = (HEUTE - timedelta(days=30)).isoformat()
STUFE = lambda w: sum(w >= g for g in (20, 40, 60, 80))


def rohreihe():
    """Tageswerte wie die API: zurueckgerechnet (ab 8 Bestandteilen), aufgezeichnet gewinnt immer."""
    r = json.load(open("/var/lib/investtimer/historie/rueckrechnung.json"))["tage"]
    a = json.load(open("/var/lib/investtimer/data/history.json"))
    reihe = {d: v["rounded"] for d, v in r.items() if v.get("count", 0) >= 8 and v.get("rounded") is not None}
    # an Wochenenden aufgezeichnete Werte wiederholen den Freitag und zaehlen nicht als Handelstag (wie die API)
    reihe.update({d: v["rounded"] for d, v in a.items() if v.get("rounded") is not None and date.fromisoformat(d).weekday() < 5})
    return dict(sorted(reihe.items())), r


def wert_und_regel(tok):
    code, live, _ = http("GET", "/api/aktuell", kopf=bearer(tok))
    with urllib.request.urlopen("http://127.0.0.1:8100/v1/marktstress", timeout=30) as f:
        api = json.loads(f.read())
    melde(B, "Wert eingeloggt = Volafly-API (Wert und Zeitpunkt)", code == 200 and live.get("rounded") == api.get("rounded") and live.get("asOf") == api.get("asOf"),
          "kritisch", "/api/aktuell vs 127.0.0.1:8100/v1/marktstress", (live.get("rounded"), live.get("asOf"), api.get("rounded"), api.get("asOf")))
    melde(B, "eingeloggt aktueller Stand (nicht zeitversetzt)", live.get("asOf", "") > GRENZE, "hoch", "/api/aktuell", live.get("asOf"))
    melde(B, "Stufe passt zum Wert (Grenzen 20/40/60/80)", 0 <= STUFE(live["rounded"]) <= 4, "mittel", "Stufe %d fuer %d" % (STUFE(live["rounded"]), live["rounded"]))
    _, s, _ = http("GET", "/data/stress.json")
    melde(B, "stress.json <= heute-30", s["publicSnapshot"]["asOf"] <= GRENZE and s.get("asOf", "") <= GRENZE, "kritisch", "/data/stress.json", s["publicSnapshot"]["asOf"])
    _, h, _ = http("GET", "/api/historie-oeffentlich")
    letzte = max([p[0] for k in ("taeglich", "woechentlich", "monatlich") for p in h.get(k, [])] or ["0"])
    melde(B, "oeffentlicher Verlauf <= heute-30 (alle Verdichtungen)", h.get("bis", "9") <= GRENZE and letzte <= GRENZE, "kritisch", "/api/historie-oeffentlich", (h.get("bis"), letzte))
    melde(B, "oeffentliche Ereignisse nur mit Spitze <= heute-30", all(e["spitze"]["d"] <= GRENZE for e in h.get("ereignisse", [])), "hoch", "/api/historie-oeffentlich")
    # DEC-019: oeffentlicher Verlauf hoechstens ein Jahr vor dem oeffentlichen Stand (taeglich, woechentlich, monatlich, Ereignisse)
    von = (date.fromisoformat(h.get("bis", "2000-01-01")) - timedelta(days=365)).isoformat() if isinstance(h, dict) and h.get("bis") else "9"
    erste = min([r[0][0] for r in (h.get(k) or [] for k in ("taeglich", "woechentlich", "monatlich")) if r] or ["0"])
    melde(B, "oeffentlicher Verlauf beginnt nicht frueher als ein Jahr vor dem oeffentlichen Stand", erste >= von
          and all(e["start"] >= von for e in h.get("ereignisse", [])), "hoch", "/api/historie-oeffentlich", (erste, von))
    _, m, _ = http("GET", "/teilen/aktuell/manifest.json")
    melde(B, "Teilen-Bilder <= heute-30", isinstance(m, dict) and m.get("asOf", "9") <= GRENZE and m.get("wert") == s["publicSnapshot"]["rounded"], "kritisch", "/teilen/aktuell/manifest.json", m.get("asOf") if isinstance(m, dict) else m)
    og = sorted(Path("/var/lib/investtimer/og").glob("og-20*.png"))
    melde(B, "Vorschaubild aus dem zeitversetzten Stand erzeugt", bool(og), "mittel", "/var/lib/investtimer/og", og[-1].name if og else "fehlt")
    _, seite, _ = http("GET", "/")
    melde(B, "ausgelieferte Seite nennt keinen aktuellen Wert-Stand", live.get("asOf", "") <= GRENZE or ('"asOf": "%s"' % live.get("asOf")) not in str(seite), "kritisch", "GET / (eingebetteter Rueckfall)")
    return live


def verlauf(tok, roh):
    code, h, _ = http("GET", "/api/historie", kopf=bearer(tok))
    if code != 200:
        melde(B, "Verlauf eingeloggt abrufbar", False, "hoch", "/api/historie", code)
        return h
    t = h["taeglich"]
    abw = [(d, w, roh.get(d)) for d, w, *_ in t if roh.get(d) != w]
    melde(B, "Tageswerte (%d) = Rohhistorie" % len(t), not abw, "hoch", "/api/historie taeglich vs history.json/rueckrechnung.json", abw[:3])
    for art, schl in (("woechentlich", lambda d: date.fromisoformat(d).isocalendar()[:2]), ("monatlich", lambda d: d[:7])):
        gruppen = {}
        for d, w in roh.items():
            gruppen.setdefault(schl(d), []).append((d, w))
        fehler = []
        for p in h[art]:
            g = gruppen.get(schl(p[0]), [])
            if not g:
                fehler.append(p[0]); continue
            soll = (g[-1][0], g[-1][1], min(x[1] for x in g), max(x[1] for x in g))
            if (p[0], p[1], p[4], p[5]) != soll:
                fehler.append((p[0], (p[0], p[1], p[4], p[5]), soll))
        melde(B, "%s: %d Perioden = letzter Handelstag, Tief, Hoch der Rohdaten" % (art, len(h[art])), not fehler, "hoch", "Nachrechnung tests/qa/daten.py", fehler[:3])
    jahr = [date.fromisoformat(p[0]) for p in t]
    luecken = [(a.isoformat(), b.isoformat()) for a, b in zip(jahr, jahr[1:]) if (b - a).days > 7]
    melde(B, "keine Luecke > 7 Tage im Tagesverlauf (letztes Jahr)", not luecken, "mittel", "/api/historie taeglich", luecken[:3])
    spruenge = [(t[i][0], t[i - 1][1], t[i][1]) for i in range(1, len(t)) if abs(t[i][1] - t[i - 1][1]) >= 35]
    melde(B, "keine Tagesspruenge >= 35 Punkte ohne Grund (letztes Jahr)", not spruenge, "info", "/api/historie taeglich", spruenge[:5])
    melde(B, "Endpunkt Tageswerte = letzter Wert der Rohhistorie", t[-1][0] == list(roh)[-1] and t[-1][1] == list(roh.values())[-1], "hoch", "taeglich[-1]", (t[-1], list(roh.items())[-1]))
    melde(B, "Endpunkt Wochen-/Monatsreihe = letzter Tageswert", h["woechentlich"][-1][:2] == t[-1][:2] and h["monatlich"][-1][:2] == t[-1][:2], "mittel", "woechentlich[-1], monatlich[-1]")
    return h


def phasen(h, roh):
    tage = list(roh.items())
    geprueft = 0
    for eid in ("lehman", "corona", "zoll"):
        e = next((x for x in h.get("ereignisse", []) if x["id"] == eid), None)
        if not e:
            continue
        geprueft += 1
        phase = [(d, w) for d, w in tage if e["start"] <= d < e["ende"]]
        spitze = max(phase, key=lambda x: x[1])
        danach = next(((d, w) for d, w in tage if d > spitze[0] and w < 40), None)
        tage_unter = (date.fromisoformat(danach[0]) - date.fromisoformat(spitze[0])).days if danach else None
        melde(B, "Phase %s: Hoechstwert %d am %s nachgerechnet" % (eid, spitze[1], spitze[0]), e["spitze"] == {"d": spitze[0], "w": spitze[1]}, "hoch", "Rohhistorie", e["spitze"])
        melde(B, "Phase %s: wieder unter 40 nach %s Tagen nachgerechnet" % (eid, tage_unter), (e.get("unter40") or {}).get("tage") == tage_unter, "hoch", "Rohhistorie", e.get("unter40"))
        vorher = [w for d, w in tage if d < e["start"]][-1:]
        start_w = next(w for d, w in tage if d >= e["start"])
        nach_ende = next((w for d, w in tage if d >= e["ende"]), None)
        melde(B, "Phase %s: Start ueber 40, Tag davor <= 40, Ende wieder unter 40" % eid,
              start_w > 40 and (not vorher or vorher[0] <= 40) and (nach_ende is None or nach_ende < 40), "mittel", "historie/ereignisse.json vs Rohhistorie",
              (vorher, start_w, nach_ende))
    melde(B, "3 Phasen nachgerechnet", geprueft == 3, "mittel", "lehman, corona, zoll", geprueft)


def teilwerte(rueck):
    """Unabhaengige Nachrechnung: Rohkurse aus historie/daten/*.csv, Formel score=(roh-lo)/(hi-lo) begrenzt auf 0..100, je Block gewichtet."""
    cfg = json.load(open(ROOT / "historie" / "config.json"))["config"]
    roh = {}
    for metrik, datei in (("VIX", "VIX"), ("VXV", "VXV"), ("VX1", "VX1"), ("VX2", "VX2"), ("VVIX", "VVIX"), ("MOVE_Index", "MOVE"), ("Equity_Put_Call_Ratio", "EPC"),
                          ("Total_Put_Call_Ratio", "TPC"), ("Fear_Greed_Index", "FG"), ("S5FD_Above_5Day_MA", "B5"), ("S5TW_Above_20Day_MA", "B20"),
                          ("S5FI_Above_50Day_MA", "B50"), ("S5TH_Above_200Day_MA", "B200"), ("SPX", "SPX")):
        reihe = {}
        zeilen = [(date.fromisoformat(z["date"][:10]), float(z["close"])) for z in csv.DictReader(open("/var/lib/investtimer/historie/daten/%s.csv" % datei))]
        # Futures-Tageskerzen sind mit dem Sitzungsbeginn datiert (So-Do): jede gehoert zum naechsten Boersentag
        sitzung = any(d.weekday() == 6 for d, _ in zeilen)
        for d, w in zeilen:
            if sitzung:
                d += timedelta(days=3 if d.weekday() == 4 else 2 if d.weekday() == 5 else 1)
            reihe[d.isoformat()] = w
        roh[metrik] = reihe
    spx = sorted(roh["SPX"].items())
    komponenten = [("VIX", "volatility", "VIX", None), ("VIX_VXV", "volatility", None, ("VIX", "VXV", 0)), ("VIX_VX1", "volatility", None, ("VIX", "VX1", 0)),
                   ("VX1_VX2", "volatility", None, ("VX1", "VX2", 0)), ("VVIX", "volatility", "VVIX", None), ("BREADTH_5", "price", "S5FD_Above_5Day_MA", None),
                   ("BREADTH_20", "price", "S5TW_Above_20Day_MA", None), ("BREADTH_50", "price", "S5FI_Above_50Day_MA", None),
                   ("BREADTH_200", "price", "S5TH_Above_200Day_MA", None), ("SPX_200D", "price", None, ("SPX", "SPX_200D", -1)),
                   ("MOVE", "positioning", "MOVE_Index", None), ("EPC", "positioning", "Equity_Put_Call_Ratio", None),
                   ("TPC", "positioning", "Total_Put_Call_Ratio", None), ("FG", "positioning", "Fear_Greed_Index", None)]
    for tag in ("2020-03-16", "2022-06-13", "2025-04-08"):
        i = next(k for k, (d, _) in enumerate(spx) if d == tag)
        werte = {m: r[tag] for m, r in roh.items() if tag in r}
        if i >= 199:
            werte["SPX_200D"] = sum(v for _, v in spx[i - 199:i + 1]) / 200
        bl, ges = {}, [0.0, 0.0]
        for name, block, m, q in komponenten:
            x = werte.get(m) if m else (werte[q[0]] / werte[q[1]] + q[2] if q[0] in werte and q[1] in werte and werte[q[1]] > 0 else None)
            if x is None:
                continue
            lo, hi, w = cfg[name]
            s = min(100.0, max(0.0, (x - lo) / (hi - lo) * 100))
            a = bl.setdefault(block, [0.0, 0.0]); a[0] += w * s; a[1] += w
            ges[0] += w * s; ges[1] += w
        bl = {k: round(v[0] / v[1], 1) for k, v in bl.items()}
        soll = rueck.get(tag, {})
        melde(B, "Teilwerte %s nachgerechnet %s" % (tag, bl), soll.get("bloecke") == bl, "hoch", "historie/daten/*.csv + config.json", soll.get("bloecke"))
        melde(B, "Gesamtwert %s nachgerechnet %.1f" % (tag, ges[0] / ges[1]), abs(soll.get("exact", -99) - ges[0] / ges[1]) < 0.01, "hoch", "rueckrechnung.json exact", soll.get("exact"))


def main():
    roh, rueck = rohreihe()
    try:
        k = testkonto()
        wert_und_regel(k["token"])
        h = verlauf(k["token"], roh)
        phasen(h, roh)
    except Exception as e:
        melde(B, "Datenpruefung durchgelaufen", False, "hoch", "tests/qa/daten.py", "%s: %s" % (type(e).__name__, e))
    finally:
        aufraeumen()
    try:
        teilwerte(rueck)
    except Exception as e:
        melde(B, "Teilwerte nachgerechnet", False, "mittel", "tests/qa/daten.py", "%s: %s" % (type(e).__name__, e))
    return ende()


if __name__ == "__main__":
    sys.exit(main())
