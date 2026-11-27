#!/usr/bin/env python3
"""Teilen-Bilder (Auftrag C, 20.11.2026): Wert, Verlauf (1M/3M/1J/5J/Alle) und Stressphasen als PNG,
je 1200x630 ("quer": Link-Vorschau, X, LinkedIn) und 1080x1350 ("hoch": Instagram/WhatsApp-Status), Deutsch und Englisch.

Standard: nur der ZEITVERSETZTE Stand (30-Tage-Regel, DEC-018) aus /data/stress.json und /v1/investtimer/historie-oeffentlich.
Ausgabe: /var/lib/investtimer/teilen/<asOf>/<name>.png plus manifest.json; jeder Stand wird genau einmal gerendert
(laeuft der Timer erneut, fehlen nur neue Dateien). Staende aelter als 60 Tage werden geloescht.
Keine Indexkurse, keine Rohwerte einzelner Indikatoren, keine Datenquellen in Bildern oder Texten.

Dateinamen: wert-<format>-<sprache>.png, verlauf-<1M|3M|1J|5J|A>-<format>-<sprache>.png, phase-<id>-<format>-<sprache>.png
Aufruf: teilen_bilder.py [--nur NAME] [--ziel DIR]. Rendering: Chrome headless (wie og_bild.py), Schriften aus public/media.
"""
import html as _html
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ZIEL = Path(os.environ.get("IT_TEILEN_DIR", "/var/lib/investtimer/teilen"))
DATEN = os.environ.get("IT_STRESS_DATEI", "/var/lib/investtimer/data/stress.json")
HISTORIE = os.environ.get("IT_HISTORIE_URL", "http://127.0.0.1:8100/v1/investtimer/historie-oeffentlich")
MEDIA = Path(os.environ.get("IT_MEDIA", "/var/www/investtimer/public/media"))
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
FORMATE = {"quer": (1200, 630), "hoch": (1080, 1350)}
SPANNEN = {"1M": (29, "taeglich"), "3M": (92, "taeglich"), "1J": (366, "woechentlich"), "5J": (1827, "woechentlich"), "A": (0, "monatlich")}
FARBEN = ["#2E6B57", "#6F7F45", "#A0722F", "#A24524", "#8E2A27"]
TEXTF = ["#2E6B57", "#687741", "#93692B", "#A24524", "#8E2A27"]
T = {
    "de": {"stufen": ["Ruhig", "Moderat", "Erhöht", "Hoch", "Panik"], "monate": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sept.", "Okt.", "Nov.", "Dez."],
           "titel": "Marktstress am US-Aktienmarkt", "titel2": ("Marktstress am", "US-Aktienmarkt"), "stand": "Stand {d}", "fuss": "investtimer.net · Keine Anlageberatung",
           "skala": ("0 · ruhig", "100 · Panik"), "verlauf": "Marktstress {z}", "hoechst": "Höchster Marktstress", "am": "{w} am {d}",
           "unter40": "Wieder unter 40", "nach": "nach {n} Tagen", "noch": "noch nicht", "von100": "von 100",
           "spannen": {"1M": "im letzten Monat", "3M": "in den letzten 3 Monaten", "1J": "in den letzten 12 Monaten", "5J": "in den letzten 5 Jahren", "A": "seit 2006"}},
    "en": {"stufen": ["Calm", "Moderate", "Elevated", "High", "Panic"], "monate": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
           "titel": "Market stress in the US stock market", "titel2": ("Market stress in the", "US stock market"), "stand": "As of {d}", "fuss": "investtimer.net · Not investment advice",
           "skala": ("0 · calm", "100 · panic"), "verlauf": "Market stress {z}", "hoechst": "Highest market stress", "am": "{w} on {d}",
           "unter40": "Back below 40", "nach": "after {n} days", "noch": "not yet", "von100": "out of 100",
           "spannen": {"1M": "over the past month", "3M": "over the past 3 months", "1J": "over the past 12 months", "5J": "over the past 5 years", "A": "since 2006"}},
}


def stufe(w):
    return sum(w >= g for g in (20, 40, 60, 80))


def datum(d, sp):
    d = date.fromisoformat(d) if isinstance(d, str) else d
    m = T[sp]["monate"][d.month - 1]
    return "%d. %s %d" % (d.day, m, d.year) if sp == "de" else "%s %d, %d" % (m, d.day, d.year)


def monat(d, sp):
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return "%s %d" % (T[sp]["monate"][d.month - 1], d.year)


def stand_zeit(iso, sp):
    """Zeitpunkt der Berechnung (UTC, ISO) als "20. Nov. 2026, 15:30" bzw. "Nov 20, 2026, 15:30" in Europe/Berlin."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    z = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Berlin"))
    return "%s, %02d:%02d" % (datum(z.date(), sp), z.hour, z.minute)


def zeitraum(e, sp):
    a, b = monat(e["start"], sp), monat(date.fromisoformat(e["ende"]) - timedelta(days=1), sp)
    return a if a == b else a + " – " + b


def esc(s):
    return _html.escape(str(s), quote=True)


def schrift(muster):
    for f in sorted(MEDIA.glob(muster)):
        return f.resolve().as_uri()
    return ""


# ── Daten ────────────────────────────────────────────────────────────────────
def laden():
    pub = (json.load(open(DATEN)).get("publicSnapshot") or {})
    with urllib.request.urlopen(HISTORIE, timeout=30) as r:
        hist = json.loads(r.read())
    if not isinstance(pub.get("rounded"), int) or not pub.get("asOf"):
        raise SystemExit("kein oeffentlicher Stand")
    return {"wert": pub["rounded"], "asOf": pub["asOf"], "historie": hist}


def auswahl(hist, spanne):
    tage, art = SPANNEN[spanne]
    reihe = hist.get(art) or []
    if not reihe:
        return [], [], art
    ende = date.fromisoformat(reihe[-1][0])
    start = ende - timedelta(days=tage) if tage else date.min
    p = [q for q in reihe if date.fromisoformat(q[0]) >= start]
    a, b = p[0][0], p[-1][0]
    e = [x for x in hist.get("ereignisse") or [] if x["ende"] > a and x["start"] <= b and a <= x["spitze"]["d"] <= b
         and (spanne != "A" or x["spitze"]["w"] >= 70)]
    return p, e, art


def phasen_reihe(hist, e):
    """Ausschnitt um die Phase: Tageswerte, wenn vorhanden, sonst Wochenwerte; 45 Tage davor und danach."""
    a = (date.fromisoformat(e["start"]) - timedelta(days=45)).isoformat()
    b = (date.fromisoformat(e["ende"]) + timedelta(days=45)).isoformat()
    t = hist.get("taeglich") or []
    if t and t[0][0] <= a:
        return [q for q in t if a <= q[0] <= b]
    # Wochenwerte: Hoechstwert der Woche, damit die Spitze der Phase auf der Linie liegt
    return [[q[0], q[5] if len(q) > 5 and q[5] is not None else q[1]] for q in hist.get("woechentlich") or [] if a <= q[0] <= b]


# ── Diagramm (SVG) ───────────────────────────────────────────────────────────
def marken(p, spanne, sp):
    a, b = date.fromisoformat(p[0][0]), date.fromisoformat(p[-1][0])
    o = []
    if spanne in ("A", "5J"):
        s = 5 if spanne == "A" else 1
        j = math.ceil(a.year / s) * s
        while date(j, 1, 1) <= b:
            if date(j, 1, 1) >= a:
                o.append((date(j, 1, 1), str(j)))
            j += s
    elif spanne in ("1J", "3M", "phase"):
        s = 3 if spanne == "1J" else 1
        j, m = a.year, a.month + 1
        while True:
            if m > 12:
                m, j = 1, j + 1
            z = date(j, m, 1)
            if z > b:
                break
            if (m - 1) % s == 0:
                o.append((z, T[sp]["monate"][m - 1] + (" " + str(j) if m == 1 or spanne == "phase" else "")))
            m += 1
    else:
        z = a
        while z <= b:
            if z.weekday() == 0:
                o.append((z, ("%d. %s" % (z.day, T[sp]["monate"][z.month - 1])) if sp == "de" else "%s %d" % (T[sp]["monate"][z.month - 1], z.day)))
            z += timedelta(days=1)
    return o


def diagramm(p, ereignisse, spanne, sp, W, H, schrift_px=17, endwert=True, markiere=None):
    """SVG mit Gitter, Achsenmarken, Baendern (Beschriftung per JS ohne Ueberlappung), Linie und Endpunkt."""
    L, R, O, U = 46, 54 if endwert else 18, 12, 34
    a, b = date.fromisoformat(p[0][0]), date.fromisoformat(p[-1][0])
    span = max(1, (b - a).days)
    x = lambda d: L + ((date.fromisoformat(d) if isinstance(d, str) else d) - a).days / span * (W - L - R)
    y = lambda w: O + (100 - w) * (H - O - U) / 100
    s = ['<svg class="chart" viewBox="0 0 %d %d" width="%d" height="%d" data-l="%d" data-r="%d">' % (W, H, W, H, L, W - R)]
    for g in (0, 25, 50, 75, 100):
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="gitter"/><text x="0" y="%.1f" class="achse">%d</text>' % (L, W - R, y(g), y(g), y(g) + schrift_px * 0.35, g))
    frei = -1e9
    for d, txt in marken(p, spanne, sp):
        xx, br = x(d), len(txt) * schrift_px * 0.58
        if xx - br / 2 < frei + 10 or xx + br / 2 > W or xx - br / 2 < 0:
            continue
        frei = xx + br / 2
        s.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="marke"/><text x="%.1f" y="%d" class="achse" text-anchor="middle">%s</text>'
                 % (xx, xx, H - U, H - U + 5, xx, H - 8, esc(txt)))
    for e in ereignisse:
        x0, x1 = max(L, x(e["start"])), min(W - R, x(e["ende"]))
        if x1 - x0 < 8:
            c = (x0 + x1) / 2
            x0 = max(L, min(W - R - 8, c - 4))
            x1 = x0 + 8
        kurz = e.get("kurz_en" if sp == "en" else "kurz") or ""
        s.append('<rect class="band%s" x="%.1f" y="%d" width="%.1f" height="%d" rx="2"/>' % (" aktiv" if markiere == e["id"] else "", x0, O, x1 - x0, H - O - U))
        if kurz and not markiere:
            s.append('<text class="bandtext" data-x0="%.1f" data-x1="%.1f" data-w="%d" y="%d">%s</text>' % (x0, x1, e["spitze"]["w"], O + schrift_px, esc(kurz)))
    s.append('<polyline class="linie" points="%s"/>' % " ".join("%.1f,%.1f" % (x(q[0]), y(q[1])) for q in p))
    if markiere:
        e = next((x_ for x_ in ereignisse if x_["id"] == markiere), None)
        if e:
            px, py = x(e["spitze"]["d"]), y(e["spitze"]["w"])
            s.append('<circle cx="%.1f" cy="%.1f" r="7" fill="%s" stroke="#f8f8f3" stroke-width="3"/>' % (px, py, FARBEN[stufe(e["spitze"]["w"])]))
    if endwert:
        z = p[-1]
        zx, zy = x(z[0]), y(z[1])
        s.append('<circle cx="%.1f" cy="%.1f" r="6" fill="%s"/><text x="%.1f" y="%.1f" class="endwert">%d</text>'
                 % (zx, zy, FARBEN[stufe(z[1])], zx + 10, min(H - U - 4, max(O + schrift_px, zy + schrift_px * 0.35)), z[1]))
    s.append("</svg>")
    return "".join(s)


# Beschriftungen der Baender: hoechste Phasen zuerst, gemessene Breite, zwei Zeilen, nie ueberlappend, nie ueber den Rand;
# am rechten Rand rechtsbuendig an der Bandkante, passt nichts: nur das Band.
LAYOUT_JS = """<script>
document.fonts.ready.then(()=>{document.querySelectorAll('svg.chart').forEach(svg=>{
 const L=+svg.dataset.l+2,R=+svg.dataset.r-2,reihen=[[],[]],zeile=parseFloat(getComputedStyle(svg.querySelector('.bandtext')||svg).fontSize)*1.25;
 [...svg.querySelectorAll('.bandtext')].sort((a,b)=>b.dataset.w-a.dataset.w).forEach(t=>{
  const x0=+t.dataset.x0,x1=+t.dataset.x1,br=t.getComputedTextLength()+2;let a=x0+4,anker='start';
  if(a+br>R){a=x1-4-br;anker='end'}
  if(a<L||a+br>R){t.remove();return}
  const r=reihen.findIndex(z=>z.every(([u,v])=>a+br<u-10||a>v+10));if(r<0){t.remove();return}
  reihen[r].push([a,a+br]);t.setAttribute('text-anchor',anker);t.setAttribute('x',anker==='end'?a+br:a);t.setAttribute('y',+t.getAttribute('y')+r*zeile)});
});document.body.dataset.fertig='1'});
</script>"""

LOGO = ('<div class="logo"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M6 34a18 18 0 0 1 36 0"/><path d="m24 34-8-13"/><circle cx="24" cy="34" r="2.4"/></svg><span>Invest<b>Timer</b></span></div>')


def seite(W, H, inhalt, extra_css=""):
    return """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Manrope;src:url(%(manrope)s)}@font-face{font-family:'DM Sans';src:url(%(dmsans)s)}
html,body{margin:0;width:%(W)dpx;height:%(H)dpx;background:#f8f8f3;color:#1b3330;font-family:'DM Sans',Arial,sans-serif;overflow:hidden;position:relative}
.logo{position:absolute;display:flex;align-items:center;gap:14px;font:600 34px Manrope,Arial,sans-serif;letter-spacing:-.5px}
.logo b{font-weight:450;color:#2e6d5c}.logo svg{width:44px;height:44px;color:#2e6d5c}
.fuss{position:absolute;color:#5f6c66;font-size:22px}
.gitter{stroke:#dfe5db;stroke-width:1.2;stroke-dasharray:3 4}.marke{stroke:#b9c3b6;stroke-width:1.2}
.achse{fill:#5f6c66;font:17px 'DM Sans',Arial,sans-serif}.endwert{fill:#1b3330;font:600 20px 'DM Sans',Arial,sans-serif}
.linie{fill:none;stroke:#2e6d5c;stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round}
.band{fill:#a0722f;opacity:.13}.band.aktiv{opacity:.17}
.bandtext{fill:#6e4f22;font:500 16px 'DM Sans',Arial,sans-serif;paint-order:stroke;stroke:#f8f8f3;stroke-width:4px;stroke-linejoin:round}
%(extra)s</style></head><body>%(inhalt)s%(js)s</body></html>""" % dict(manrope=schrift("*.ttf"), dmsans=schrift("*.woff2"), W=W, H=H, inhalt=inhalt, extra=extra_css, js=LAYOUT_JS)


def bogen_svg(w, breite, hoehe):
    s = stufe(w)
    a = math.radians(180 + max(0, min(100, w)) * 1.8)
    px, py = 250 + 200 * math.cos(a), 250 + 200 * math.sin(a)
    return ('<svg viewBox="0 0 500 290" width="%d" height="%d"><path d="M50 250 A200 200 0 0 1 450 250" fill="none" stroke="#dfe5db" stroke-width="12" stroke-linecap="round"/>'
            '<path d="M50 250 A200 200 0 0 1 %.1f %.1f" fill="none" stroke="%s" stroke-width="12" stroke-linecap="round"/>'
            '<circle cx="%.1f" cy="%.1f" r="12" fill="%s" stroke="#f8f8f3" stroke-width="4"/></svg>') % (breite, hoehe, px, py, FARBEN[s], px, py, FARBEN[s])


def html_wert(d, fmt, sp):
    t, w = T[sp], d["wert"]
    s = stufe(w)
    W, H = FORMATE[fmt]
    stand = t["stand"].format(d=stand_zeit(d["zeit"], sp) if d.get("zeit") else datum(d["asOf"], sp))
    st = '<span class="stufe" style="color:%s"><i style="background:%s"></i>%s</span>' % (TEXTF[s], FARBEN[s], t["stufen"][s])
    if fmt == "quer":
        inhalt = (LOGO.replace('class="logo"', 'class="logo" style="left:72px;top:58px"')
                  + '<div style="position:absolute;left:72px;top:190px;width:520px"><p class="titel">%s<br><span style="white-space:nowrap">%s</span></p>%s<p class="stand">%s</p></div>' % (esc(t["titel2"][0]), esc(t["titel2"][1]), st, esc(stand))
                  + '<div style="position:absolute;left:640px;top:118px">%s</div>' % bogen_svg(w, 500, 290)
                  + '<div class="zahl" style="left:640px;top:205px;width:500px;font-size:190px">%d</div>' % w
                  + '<div class="skala" style="left:690px;top:430px;width:400px">%s</div>' % "".join("<span>%s</span>" % esc(x) for x in t["skala"])
                  + '<div class="fuss" style="left:72px;bottom:50px">%s</div>' % esc(t["fuss"]))
        css = ".titel{font:500 52px/1.12 Manrope,Arial,sans-serif;letter-spacing:-1.4px;margin:0 0 26px}.stand{margin:26px 0 0;font-size:26px;color:#5f6c66}"
    else:
        inhalt = (LOGO.replace('class="logo"', 'class="logo" style="left:80px;top:80px"')
                  + '<p class="titel" style="position:absolute;left:80px;top:200px;width:920px">%s</p>' % esc(t["titel"])
                  + '<div style="position:absolute;left:140px;top:420px">%s</div>' % bogen_svg(w, 800, 464)
                  + '<div class="zahl" style="left:140px;top:560px;width:800px;font-size:270px">%d</div>' % w
                  + '<div class="skala" style="left:220px;top:900px;width:640px">%s</div>' % "".join("<span>%s</span>" % esc(x) for x in t["skala"])
                  + '<div style="position:absolute;left:80px;top:1010px;width:920px;text-align:center">%s<p class="stand">%s</p></div>' % (st, esc(stand))
                  + '<div class="fuss" style="left:80px;bottom:72px;font-size:26px">%s</div>' % esc(t["fuss"]))
        css = ".titel{font:500 64px/1.12 Manrope,Arial,sans-serif;letter-spacing:-1.6px;margin:0}.stand{margin:22px 0 0;font-size:32px;color:#5f6c66}.stufe{font-size:40px!important}"
    css += (".zahl{position:absolute;text-align:center;font-family:Manrope,Arial,sans-serif;font-weight:450;line-height:1;letter-spacing:-6px}"
            ".skala{position:absolute;display:flex;justify-content:space-between;font-size:22px;color:#5f6c66}"
            ".stufe{display:inline-flex;align-items:center;gap:12px;font-size:32px;font-weight:500}.stufe i{width:15px;height:15px;border-radius:50%}")
    return seite(W, H, inhalt, css)


def html_verlauf(d, spanne, fmt, sp):
    t = T[sp]
    W, H = FORMATE[fmt]
    p, e, _ = auswahl(d["historie"], spanne)
    if not p:
        return None
    titel = t["verlauf"].format(z=t["spannen"][spanne])
    stand = t["stand"].format(d=stand_zeit(d["zeit"], sp) if d.get("zeit") else datum(p[-1][0], sp))
    if fmt == "quer":
        kopf = LOGO.replace('class="logo"', 'class="logo" style="left:60px;top:40px;font-size:28px"').replace("width:44px", "width:36px")
        inhalt = (kopf + '<div style="position:absolute;right:60px;top:46px;font-size:22px;color:#5f6c66">%s</div>' % esc(stand)
                  + '<p class="titel" style="left:60px;top:104px">%s</p>' % esc(titel)
                  + '<div style="position:absolute;left:44px;top:170px">%s</div>' % diagramm(p, e, spanne, sp, 1110, 390)
                  + '<div class="fuss" style="left:60px;bottom:28px">%s</div>' % esc(t["fuss"]))
        css = ".titel{position:absolute;margin:0;font:500 40px/1.15 Manrope,Arial,sans-serif;letter-spacing:-1px}"
    else:
        inhalt = (LOGO.replace('class="logo"', 'class="logo" style="left:80px;top:80px"')
                  + '<p class="titel" style="left:80px;top:200px;width:920px">%s</p>' % esc(titel)
                  + '<p style="position:absolute;left:80px;top:%dpx;margin:0;font-size:30px;color:#5f6c66">%s</p>' % (360 if len(titel) > 28 else 290, esc(stand))
                  + '<div style="position:absolute;left:40px;top:470px">%s</div>' % diagramm(p, e, spanne, sp, 1000, 640, schrift_px=20)
                  + '<div class="fuss" style="left:80px;bottom:72px;font-size:26px">%s</div>' % esc(t["fuss"]))
        css = (".titel{position:absolute;margin:0;font:500 62px/1.14 Manrope,Arial,sans-serif;letter-spacing:-1.5px}"
               ".achse{font-size:20px}.bandtext{font-size:19px}.endwert{font-size:24px}.linie{stroke-width:3.2}")
    return seite(W, H, inhalt, css)


def html_phase(d, eid, fmt, sp):
    t = T[sp]
    W, H = FORMATE[fmt]
    e = next((x for x in d["historie"].get("ereignisse") or [] if x["id"] == eid), None)
    if not e:
        return None
    p = phasen_reihe(d["historie"], e)
    if len(p) < 3:
        return None
    name = e.get("name_en" if sp == "en" else "name") or e["name"]
    sw = e["spitze"]["w"]
    hoechst = t["am"].format(w=sw, d=datum(e["spitze"]["d"], sp))
    unter = t["nach"].format(n=e["unter40"]["tage"]) if e.get("unter40") else t["noch"]
    zahlen = ('<dl class="zahlen"><div><dt>%s</dt><dd><i style="background:%s"></i>%s</dd></div><div><dt>%s</dt><dd>%s</dd></div></dl>'
              % (esc(t["hoechst"]), FARBEN[stufe(sw)], esc(hoechst), esc(t["unter40"]), esc(unter)))
    if fmt == "quer":
        inhalt = (LOGO.replace('class="logo"', 'class="logo" style="left:60px;top:40px;font-size:28px"').replace("width:44px", "width:36px")
                  + '<p class="titel" style="left:60px;top:108px;width:1080px">%s</p><p class="zeit" style="left:60px;top:168px">%s</p>' % (esc(name), esc(zeitraum(e, sp)))
                  + '<div style="position:absolute;left:60px;top:250px;width:380px">%s</div>' % zahlen
                  + '<div style="position:absolute;left:440px;top:226px">%s</div>' % diagramm(p, [e], "phase", sp, 710, 330, endwert=False, markiere=e["id"])
                  + '<div class="fuss" style="left:60px;bottom:28px">%s</div>' % esc(t["fuss"]))
        css = (".titel{position:absolute;margin:0;font:500 46px/1.15 Manrope,Arial,sans-serif;letter-spacing:-1.2px}"
               ".zeit{position:absolute;margin:0;font-size:26px;color:#5f6c66}.zahlen{margin:0;display:grid;gap:30px}.zahlen dt{font-size:22px;color:#5f6c66}"
               ".zahlen dd{margin:6px 0 0;font-size:32px;display:flex;align-items:center;gap:12px}.zahlen i{width:14px;height:14px;border-radius:50%;flex:none}")
    else:
        inhalt = (LOGO.replace('class="logo"', 'class="logo" style="left:80px;top:80px"')
                  + '<p class="titel" style="left:80px;top:200px;width:920px">%s</p><p class="zeit" style="left:80px;top:%dpx">%s</p>'
                  % (esc(name), 360 if len(name) > 26 else 290, esc(zeitraum(e, sp)))
                  + '<div style="position:absolute;left:40px;top:470px">%s</div>' % diagramm(p, [e], "phase", sp, 1000, 470, schrift_px=20, endwert=False, markiere=e["id"])
                  + '<div style="position:absolute;left:80px;top:1000px;width:920px">%s</div>' % zahlen
                  + '<div class="fuss" style="left:80px;bottom:72px;font-size:26px">%s</div>' % esc(t["fuss"]))
        css = (".titel{position:absolute;margin:0;font:500 62px/1.14 Manrope,Arial,sans-serif;letter-spacing:-1.5px}"
               ".zeit{position:absolute;margin:0;font-size:32px;color:#5f6c66}.zahlen{margin:0;display:grid;grid-template-columns:1fr 1fr;gap:30px}"
               ".zahlen dt{font-size:26px;color:#5f6c66}.zahlen dd{margin:8px 0 0;font-size:36px;display:flex;align-items:center;gap:12px}"
               ".zahlen i{width:16px;height:16px;border-radius:50%;flex:none}.achse{font-size:20px}.linie{stroke-width:3.2}")
    return seite(W, H, inhalt, css)


def varianten(d):
    """Alle Bilder eines Stands: (name, html-Funktion, Argumente)."""
    aus = []
    for sp in ("de", "en"):
        for fmt in FORMATE:
            aus.append(("wert-%s-%s" % (fmt, sp), html_wert, (d, fmt, sp)))
            for z in SPANNEN:
                aus.append(("verlauf-%s-%s-%s" % (z, fmt, sp), html_verlauf, (d, z, fmt, sp)))
            for e in d["historie"].get("ereignisse") or []:
                aus.append(("phase-%s-%s-%s" % (e["id"], fmt, sp), html_phase, (d, e["id"], fmt, sp)))
    return aus


BILD_PY = os.environ.get("IT_BILD_PY", "/opt/investtimer-bild/bin/python")
OPTIMIEREN = ("import sys;from PIL import Image;im=Image.open(sys.argv[1]).convert('RGB');"
              "im.quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).save(sys.argv[1],optimize=True)")


def optimieren(pfad):
    """PNG mit 128-Farben-Palette (Diagramme/Text bleiben scharf): typisch 50-60 % kleiner, Ziel < 150 KB. Ohne Pillow-Umgebung: unveraendert."""
    if os.path.exists(BILD_PY):
        subprocess.run(["nice", "-n", "10", BILD_PY, "-c", OPTIMIEREN, str(pfad)], capture_output=True, timeout=60)


def rendern(html_text, W, H, ziel):
    with tempfile.TemporaryDirectory() as tmp:
        seite_ = Path(tmp) / "s.html"
        seite_.write_text(html_text, encoding="utf-8")
        bild = Path(tmp) / "b.png"
        subprocess.run(["nice", "-n", "10", CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--virtual-time-budget=4000", "--window-size=%d,%d" % (W, H), "--screenshot=" + str(bild), seite_.as_uri()],
                       check=True, capture_output=True, timeout=90)
        optimieren(bild)
        shutil.copy(bild, ziel)
    os.chmod(ziel, 0o644)


def manifest(d):
    hist = d["historie"]
    return {"asOf": d["asOf"], "wert": d["wert"], "stufe": stufe(d["wert"]), "zeit": d.get("zeit"),
            "spannen": {z: (auswahl(hist, z)[0] or [[None]])[-1][0] for z in SPANNEN},
            "phasen": {e["id"]: {"name": e["name"], "name_en": e.get("name_en") or e["name"], "start": e["start"], "ende": e["ende"],
                                 "spitze": e["spitze"], "unter40": e.get("unter40")} for e in hist.get("ereignisse") or []}}


def main():
    args = sys.argv[1:]
    if "--optimieren" in args:   # bestehende Bilder einmalig verkleinern
        n = 0
        for f in Path(args[args.index("--optimieren") + 1] if len(args) > args.index("--optimieren") + 1 else ZIEL).rglob("*.png"):
            vorher = f.stat().st_size
            optimieren(f)
            n += 1
            print("%s %d -> %d KB" % (f.name, vorher // 1024, f.stat().st_size // 1024))
        print("ok: %d Bilder optimiert" % n)
        return
    nur = args[args.index("--nur") + 1] if "--nur" in args else None
    ziel_basis = Path(args[args.index("--ziel") + 1]) if "--ziel" in args else ZIEL
    d = laden()
    ordner = ziel_basis / d["asOf"]
    ordner.mkdir(parents=True, exist_ok=True)
    os.chmod(ziel_basis, 0o755)
    os.chmod(ordner, 0o755)
    neu = 0
    for name, fn, a in varianten(d):
        if nur and not name.startswith(nur):
            continue
        datei = ordner / (name + ".png")
        if datei.exists() and not nur:
            continue
        h = fn(*a)
        if h is None:
            continue
        fmt = "quer" if "-quer-" in name else "hoch"
        rendern(h, *FORMATE[fmt], datei)
        neu += 1
    (ordner / "manifest.json").write_text(json.dumps(manifest(d), ensure_ascii=False), encoding="utf-8")
    os.chmod(ordner / "manifest.json", 0o644)
    neueste = ziel_basis / "aktuell"
    if neueste.is_symlink() or neueste.exists():
        neueste.unlink()
    neueste.symlink_to(ordner.name)
    live = ziel_basis / "live"
    if live.is_dir():   # Live-Staende (aktueller Wert, eingeloggt geteilt) 30 Tage
        for alt in live.iterdir():
            if alt.is_dir() and time.time() - alt.stat().st_mtime > 30 * 86400:
                shutil.rmtree(alt)
    for alt in ziel_basis.iterdir():
        if alt.is_dir() and not alt.is_symlink() and alt.name[:2] == "20" and time.time() - alt.stat().st_mtime > 60 * 86400:
            shutil.rmtree(alt)
    print("ok: Stand %s, %d neue Bilder in %s" % (d["asOf"], neu, ordner))


if __name__ == "__main__":
    main()
