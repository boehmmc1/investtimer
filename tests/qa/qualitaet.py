#!/usr/bin/env python3
"""QA Bereich 5 – Qualitaet und Darstellung.
- tools/check_mobile.py --voll: alle UI-Tests plus Gesamtpruefung (320/375/390/430/768/1024/1280/1440 px, Querformat, offene Tastatur,
  ausgeloggt/eingeloggt, DE/EN: nichts abgeschnitten/ueberdeckt/ueberlappend, kein horizontales Scrollen, Konsolen- und Netzfehler 0).
- axe-core (WCAG 2.1 AA) auf der Live-Seite, alle Ansichten, 390 und 1280 px: keine schweren Befunde (critical/serious).
- Lighthouse mobil (Slow-4G-Simulation) und Desktop: Performance, Barrierefreiheit, Best Practices, SEO; Seitengewicht, Caching-Header.
Werkzeuge in /opt/investtimer-qa (venv mit Playwright, node_modules mit lighthouse und axe-core).
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ROOT, SEITE, CHROME, AUSGABE, melde, http, ende  # noqa: E402

B = "5 Qualitaet"
QA = Path(os.environ.get("QA_WERKZEUGE", "/opt/investtimer-qa"))
ANSICHTEN = ["", "#ki", "#verlauf", "#konto", "#faq", "#feedback"]


def ui_tests():
    r = subprocess.run([str(QA / "venv/bin/python"), str(ROOT / "tools/check_mobile.py"), "--voll"], capture_output=True, text=True, timeout=5400, cwd=ROOT)
    (AUSGABE / "check_mobile.txt").write_text(r.stdout + r.stderr)
    for z in r.stdout.splitlines():
        if z.startswith(("ok   ", "FEHL ")) and not z.startswith(("ok   Gesamtpruefung", "FEHL Gesamtpruefung")):
            melde(B, "UI-Test " + z[5:].split(":")[0], z.startswith("ok"), "hoch", "tools/check_mobile.py --voll", z[5:200])
        if "Gesamtpruefung" in z:
            melde(B, "Gesamtpruefung 9 Groessen x Ansichten x aus/ein x DE/EN", z.startswith("ok"), "hoch", "tests/ui/test_gesamt.py --voll", z.strip())
    melde(B, "check_mobile --voll ohne Auffaelligkeiten", "SUMME keine Auffaelligkeiten" in r.stdout, "hoch", "check_mobile.txt", r.stdout[-300:])


async def axe():
    from playwright.async_api import async_playwright
    quelle = (QA / "node_modules/axe-core/axe.min.js").read_text()
    alle = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        for w in (390, 1280):
            # bypass_csp: axe-core wird als Skript eingeschleust; die CSP der Seite wuerde das (richtigerweise) verbieten
            ctx = await b.new_context(viewport={"width": w, "height": 900}, is_mobile=w < 760, has_touch=w < 760, bypass_csp=True)
            pg = await ctx.new_page()
            await pg.goto(SEITE + "/")
            await pg.wait_for_timeout(1500)
            for a in ANSICHTEN + ["/impressum.html", "/datenschutz.html"]:
                if a.startswith("/"):
                    await pg.goto(SEITE + a)
                else:
                    await pg.evaluate("h=>{location.hash=h;if(!h)history.pushState(null,'',location.pathname)}", a)
                await pg.wait_for_timeout(1200)
                await pg.add_script_tag(content=quelle)
                r = await pg.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});
                    return r.violations.map(v=>({id:v.id,impact:v.impact,hilfe:v.help,n:v.nodes.length,beispiel:v.nodes[0]&&v.nodes[0].target.join(' ')}))}""")
                name = "%d %s" % (w, a or "Start")
                alle[name] = r
                schwer = [v for v in r if v["impact"] in ("critical", "serious")]
                melde(B, "axe %s: keine schweren Befunde" % name, not schwer, "mittel", "axe-core 4 WCAG 2.1 AA", ["%s (%s, %dx) %s" % (v["id"], v["impact"], v["n"], v["beispiel"]) for v in schwer][:4])
                leicht = [v for v in r if v["impact"] not in ("critical", "serious")]
                if leicht:
                    melde(B, "axe %s: leichte Befunde" % name, False, "info", "axe-core", ["%s (%s)" % (v["id"], v["impact"]) for v in leicht][:4])
            await ctx.close()
        await b.close()
    (AUSGABE / "axe.json").write_text(json.dumps(alle, ensure_ascii=False, indent=1))


def lighthouse():
    erg = {}
    for modus in ("mobil", "desktop"):
        datei = AUSGABE / ("lighthouse-%s.json" % modus)
        befehl = [str(QA / "node_modules/.bin/lighthouse"), SEITE + "/", "--quiet", "--output=json", "--output-path=" + str(datei),
                  "--chrome-flags=--headless=new --no-sandbox", "--only-categories=performance,accessibility,best-practices,seo"]
        if modus == "desktop":
            befehl.append("--preset=desktop")
        r = subprocess.run(befehl, capture_output=True, text=True, timeout=600, env=dict(os.environ, CHROME_PATH=CHROME, PATH="/opt/node22/bin:" + os.environ["PATH"]))
        if not datei.exists():
            melde(B, "Lighthouse %s gelaufen" % modus, False, "mittel", "lighthouse", r.stderr[-300:])
            continue
        j = json.loads(datei.read_text())
        punkte = {k: round((v.get("score") or 0) * 100) for k, v in j["categories"].items()}
        a = j["audits"]
        werte = {"FCP": a["first-contentful-paint"]["displayValue"], "LCP": a["largest-contentful-paint"]["displayValue"],
                 "TBT": a["total-blocking-time"]["displayValue"], "CLS": a["cumulative-layout-shift"]["displayValue"],
                 "Gewicht": a["total-byte-weight"]["displayValue"]}
        erg[modus] = {"punkte": punkte, "werte": werte}
        for k, v in punkte.items():
            melde(B, "Lighthouse %s %s: %d" % (modus, k, v), v >= 90, "mittel" if v < 70 else "niedrig", "lighthouse-%s.json" % modus, werte if k == "performance" else "")
    (AUSGABE / "lighthouse.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1))


def caching():
    for pfad, muss in (("/", "no-cache"), ("/sw.js", "no-cache"), ("/data/stress.json", ""), ("/teilen/aktuell/manifest.json", "no-cache")):
        _, _, h = http("GET", pfad)
        cc = {k.lower(): v for k, v in h.items()}.get("cache-control", "")
        melde(B, "Cache-Control %s: %s" % (pfad, cc or "fehlt"), muss in cc if muss else bool(cc), "niedrig", "curl -sI " + pfad)
    _, seite, h = http("GET", "/")
    media = sorted(set(__import__("re").findall(r'/media/[0-9a-f]{8,}[^"\')\s]*', str(seite))))
    if media:
        _, _, hm = http("GET", media[0])
        cc = {k.lower(): v for k, v in hm.items()}.get("cache-control", "")
        melde(B, "versionierte Dateien lange cachebar (%s)" % cc, "max-age=31536000" in cc or "immutable" in cc, "niedrig", "curl -sI " + media[0])
    enc = {k.lower(): v for k, v in http("GET", "/", kopf={"Accept-Encoding": "gzip"})[2].items()}.get("content-encoding", "")
    melde(B, "Seite komprimiert ausgeliefert (gzip/br)", enc in ("gzip", "br"), "mittel", "Accept-Encoding: gzip", enc or "unkomprimiert")


def main():
    for f in (caching, lambda: asyncio.run(axe()), lighthouse, ui_tests):
        try:
            f()
        except Exception as e:
            melde(B, "Pruefblock durchgelaufen", False, "mittel", "tests/qa/qualitaet.py", "%s: %s" % (type(e).__name__, e))
    return ende()


if __name__ == "__main__":
    sys.exit(main())
