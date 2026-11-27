#!/usr/bin/env python3
"""Vorschaubild zum Teilen (Open Graph, 1200x630), taeglich per Timer investtimer-og.

Zeigt nur den ZEITVERSETZTEN Wert (publicSnapshot aus /data/stress.json, 30-Tage-Regel, DEC-018), nie den aktuellen. Logo, Bogen in der
Stufenfarbe, Wert, Stufe, "Stand {Datum}", "Marktstress am US-Aktienmarkt". Keine Indexnamen, keine Datenquellen.
Ausgabe: /var/lib/investtimer/og/og-JJJJ-MM-TT.png (Datum = UTC-Tag der Erzeugung, nginx setzt es in die Seite ein)
und og-aktuell.png als Rueckfall; Bilder aelter als 14 Tage werden geloescht. Rendering: Chrome headless (keine Zusatzpakete).
"""
import json, math, os, shutil, subprocess, sys, tempfile, time
from datetime import date, datetime, timezone
from pathlib import Path

ZIEL = Path(os.environ.get("IT_OG_DIR", "/var/lib/investtimer/og"))
DATEN = os.environ.get("IT_STRESS_DATEI", "/var/lib/investtimer/data/stress.json")
MEDIA = Path(os.environ.get("IT_MEDIA", "/var/www/investtimer/public/media"))
FARBEN = ["#2E6B57", "#6F7F45", "#A0722F", "#A24524", "#8E2A27"]
TEXT = ["#2E6B57", "#687741", "#93692B", "#A24524", "#8E2A27"]
STUFEN = ["Ruhig", "Moderat", "Erhöht", "Hoch", "Panik"]
MONATE = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sept.", "Okt.", "Nov.", "Dez."]


def schrift(muster):
    for f in sorted(MEDIA.glob(muster)):
        return f.resolve().as_uri()
    return ""


def html(wert, as_of):
    s = sum(wert >= g for g in (20, 40, 60, 80))
    d = date.fromisoformat(as_of)
    datum = "%d. %s %d" % (d.day, MONATE[d.month - 1], d.year)
    # Bogen wie auf der Seite: 180 Grad, Mittelpunkt (250,250), Radius 200, gefuellt bis zum Wert
    w = max(0.0, min(100.0, float(wert)))
    a = math.radians(180 + w * 1.8)
    px, py = 250 + 200 * math.cos(a), 250 + 200 * math.sin(a)
    gross = 1 if w > 100 else 0
    manrope, dmsans = schrift("*.ttf"), schrift("*.woff2")
    return """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Manrope;src:url(%(manrope)s)}@font-face{font-family:'DM Sans';src:url(%(dmsans)s)}
html,body{margin:0;width:1200px;height:630px;background:#f8f8f3;color:#1b3330;font-family:'DM Sans',Arial,sans-serif;overflow:hidden}
.logo{position:absolute;left:72px;top:58px;display:flex;align-items:center;gap:14px;font:600 34px Manrope,Arial,sans-serif;letter-spacing:-.5px}
.logo b{font-weight:450;color:#2e6d5c}.logo svg{width:44px;height:44px;color:#2e6d5c}
.bogen{position:absolute;left:640px;top:120px;width:500px;height:300px}
.zahl{position:absolute;left:640px;top:205px;width:500px;text-align:center;font:450 190px/1 Manrope,Arial,sans-serif;letter-spacing:-6px}
.links{position:absolute;left:72px;top:212px;width:520px}
.titel{font:500 52px/1.12 Manrope,Arial,sans-serif;letter-spacing:-1.4px;margin:0 0 26px}
.stufe{display:inline-flex;align-items:center;gap:12px;font-size:30px;font-weight:500;color:%(text)s}
.stufe:before{content:'';width:14px;height:14px;border-radius:50%%;background:%(farbe)s}
.stand{position:absolute;left:72px;bottom:56px;font-size:24px;color:#5f6c66}
.skala{position:absolute;left:690px;top:445px;width:400px;display:flex;justify-content:space-between;font-size:20px;color:#5f6c66}
</style></head><body>
<div class="logo"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M6 34a18 18 0 0 1 36 0"/><path d="m24 34-8-13"/><circle cx="24" cy="34" r="2.4"/></svg><span>Invest<b>Timer</b></span></div>
<div class="links"><p class="titel">Marktstress am<br><span style="white-space:nowrap">US-Aktienmarkt</span></p><span class="stufe">%(stufe)s</span></div>
<svg class="bogen" viewBox="0 0 500 300"><path d="M50 250 A200 200 0 0 1 450 250" fill="none" stroke="#dfe5db" stroke-width="10" stroke-linecap="round"/>
<path d="M50 250 A200 200 0 %(gross)d 1 %(px).1f %(py).1f" fill="none" stroke="%(farbe)s" stroke-width="10" stroke-linecap="round"/>
<circle cx="%(px).1f" cy="%(py).1f" r="11" fill="%(farbe)s" stroke="#f8f8f3" stroke-width="4"/></svg>
<div class="zahl">%(wert)d</div><div class="skala"><span>0 · ruhig</span><span>100 · Panik</span></div>
<div class="stand">Stand %(datum)s · zeitversetzt · Keine Anlageberatung</div>
</body></html>""" % dict(manrope=manrope, dmsans=dmsans, farbe=FARBEN[s], text=TEXT[s], stufe=STUFEN[s], wert=round(w), px=px, py=py, gross=gross, datum=datum)


def main():
    pub = (json.load(open(DATEN)).get("publicSnapshot") or {})
    wert, as_of = pub.get("rounded"), pub.get("asOf")
    if not isinstance(wert, int) or not as_of:
        sys.exit("kein oeffentlicher Stand")
    ZIEL.mkdir(parents=True, exist_ok=True)
    heute = datetime.now(timezone.utc).date().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        seite = Path(tmp) / "og.html"
        seite.write_text(html(wert, as_of), encoding="utf-8")
        bild = Path(tmp) / "og.png"
        subprocess.run([os.environ.get("CHROME", "/usr/bin/google-chrome"), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", "--window-size=1200,630", "--screenshot=" + str(bild), seite.as_uri()],
                       check=True, capture_output=True, timeout=60)
        ziel = ZIEL / ("og-%s.png" % heute)
        shutil.copy(bild, ziel)
        shutil.copy(bild, ZIEL / "og-aktuell.png")
    os.chmod(ziel, 0o644); os.chmod(ZIEL / "og-aktuell.png", 0o644)
    for f in ZIEL.glob("og-20*.png"):
        if time.time() - f.stat().st_mtime > 14 * 86400:
            f.unlink()
    print("ok: %s (%d Bytes) Wert %d vom %s" % (ziel, ziel.stat().st_size, wert, as_of))


if __name__ == "__main__":
    main()
