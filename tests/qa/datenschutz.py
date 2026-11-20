#!/usr/bin/env python3
"""QA Bereich 4 – Datenschutz und Recht (Live-Seite, ein Testkonto, KI-Stichproben ueber die eigene Testinstanz).
- Mitschnitt ausgeloggt/eingeloggt (390/1280 px, alle Ansichten): Fremdabrufe, Cookies, Speicher (localStorage, sessionStorage,
  IndexedDB, Cache Storage), Fremdskripte.
- Sprache: keine Empfehlungs- oder Timing-Begriffe in sichtbaren Texten (DE/EN, aus/ein), FAQ, Rechtstexten, Alarm-/Push-/Mail-Vorlagen,
  Teilen-Texten, vorbereiteten KI-Antworten und 10 echten KI-Antworten (Verneinungen wie "keine Kaufempfehlung" sind erlaubt).
- Keine Datenquellen, Indexnamen oder Rohwerte in oeffentlich sichtbaren Texten.
- Impressum vollstaendig (Strasse, PLZ/Ort, E-Mail) und in jeder Ansicht in der Fusszeile erreichbar; KI-Kennzeichnung im KI-Bereich.
Der Abgleich der Datenschutzerklaerung mit der Wirklichkeit steht als Liste im Bericht (Sichtpruefung, nicht automatisierbar).
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ROOT, SEITE, CHROME, AUSGABE, melde, http, testkonto, aufraeumen, ende  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

B = "4 Datenschutz"
ERLAUBTE_HOSTS = {"investtimer.net", "owcmsgroqhawcjlehcjk.supabase.co"}
ANSICHTEN = ["", "#ki", "#verlauf", "#konto", "#faq", "#feedback"]
# Empfehlungs-/Timing-Sprache; ein Treffer zaehlt nicht, wenn kurz davor verneint wird ("keine Kauf- oder Verkaufsempfehlung")
EMPF = [r"\bkauf(en|t|e|signal|empfehlung|gelegenheit|zeitpunkt)\b", r"\bverkauf(en|t|e|ssignal|sempfehlung)\b", r"\bEinstieg\w*", r"\beinsteigen\b",
        r"\bAusstieg\w*", r"\baussteigen\b", r"\bChance(n)?\b", r"\bKaufsignal\w*", r"\bGelegenheit\b", r"\bSchnäppchen\b", r"\bjetzt investieren\b",
        r"\bguter Zeitpunkt\b", r"\brichtige[nr]? Zeitpunkt\b", r"\bbuy(ing)?\b", r"\bsell(ing)?\b", r"\bentry point\b", r"\bopportunit(y|ies)\b",
        r"\bgood time to\b", r"\bbuy signal\b", r"\bbottom(ed)?\b"]
NEGATION = re.compile(r"(kein|keine|keinen|nicht|weder|ohne|no|not|never|doesn’t|doesn't|don’t|don't|isn’t|won’t|can’t|can't|cannot|neither)\b[^.!?]{0,60}$", re.I)
QUELLEN = [r"\bVIX\b", r"\bVVIX\b", r"\bVXV\b", r"\bMOVE\b", r"S&P", r"\bSPX\b", r"\bNasdaq\b", r"Put/Call", r"Put-Call", r"Fear\s*&\s*Greed",
           r"\bCBOE\b", r"\bCboe\b", r"TradingView", r"\bCNN\b", r"Barchart", r"Bloomberg", r"\bFRED\b"]


def sprache_pruefen(quelle, text, schwere="hoch"):
    funde = []
    for m_ in EMPF:
        for t in re.finditer(m_, text, re.I):
            vor = text[max(0, t.start() - 80):t.start()]
            if NEGATION.search(vor):
                continue
            funde.append(text[max(0, t.start() - 40):t.end() + 30].replace("\n", " "))
    melde(B, "keine Empfehlungs-/Timing-Sprache: %s" % quelle, not funde, schwere, quelle, funde[:3])
    return funde


def quellen_pruefen(quelle, text):
    funde = sorted({t.group(0) for m_ in QUELLEN for t in re.finditer(m_, text)})
    melde(B, "keine Datenquellen/Indexnamen: %s" % quelle, not funde, "hoch", quelle, funde)


async def mitschnitt(konto):
    texte = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        for ein in (False, True):
            for w in (390, 1280):
                ctx = await b.new_context(viewport={"width": w, "height": 900}, is_mobile=w < 760, has_touch=w < 760)
                pg = await ctx.new_page()
                hosts, skripte = set(), set()
                pg.on("request", lambda r: hosts.add(re.sub(r"^https?://([^/:]+).*", r"\1", r.url)) if r.url.startswith("http") else None)
                pg.on("request", lambda r: skripte.add(r.url) if r.resource_type == "script" and not r.url.startswith(SEITE) else None)
                await pg.goto(SEITE + "/")
                await pg.wait_for_timeout(1500)
                if ein:
                    await pg.evaluate("([e,p])=>window.InvestTimer.mitPasswort(e,p)", [konto["email"], konto["passwort"]])
                    await pg.reload()
                    await pg.wait_for_timeout(2500)
                for sp in ("de", "en"):
                    if sp == "en":
                        await pg.evaluate("()=>{const h=document.querySelector('#header-language');if(h){h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}}")
                        await pg.wait_for_timeout(400)
                    for a in ANSICHTEN:
                        await pg.evaluate("h=>{location.hash=h;if(!h)history.pushState(null,'',location.pathname)}", a)
                        await pg.wait_for_timeout(1300)
                        if a == "#faq":
                            await pg.evaluate("()=>document.querySelectorAll('.faq-frage[aria-expanded=false]').forEach(b=>b.click())")
                            await pg.wait_for_timeout(300)
                        t = await pg.evaluate("document.body.innerText")
                        texte["%s %s %s %s" % ("ein" if ein else "aus", w, sp, a or "#start")] = t
                        fuss = await pg.evaluate("[...document.querySelectorAll('a[href*=impressum]')].some(x=>x.offsetParent!==null)")
                        if w == 1280 and sp == "de":
                            melde(B, "Impressum-Link sichtbar: %s %s" % ("ein" if ein else "aus", a or "Start"), fuss, "hoch", "a[href*=impressum] sichtbar")
                        if a == "#ki" and w == 1280:
                            melde(B, "KI-Kennzeichnung im KI-Bereich (%s, %s)" % ("ein" if ein else "aus", sp),
                                  ("Antworten erzeugt eine KI" in t) if sp == "de" else ("AI-generated answers" in t), "hoch", "#ki innerText")
                kekse = await ctx.cookies()
                speicher = await pg.evaluate("""async()=>({ls:Object.keys(localStorage),ss:Object.keys(sessionStorage),cookie:document.cookie,
                    idb:(indexedDB.databases?(await indexedDB.databases()).map(d=>d.name):[]),caches:await caches.keys()})""")
                tag = "%s %d" % ("eingeloggt" if ein else "ausgeloggt", w)
                fremd = sorted(h for h in hosts if h not in ERLAUBTE_HOSTS)
                melde(B, "keine Fremdabrufe (%s)" % tag, not fremd, "kritisch", "Playwright-Mitschnitt aller Ansichten", fremd)
                melde(B, "Supabase nur eingeloggt angesprochen (%s)" % tag, ein or "owcmsgroqhawcjlehcjk.supabase.co" not in hosts, "mittel", "Mitschnitt", sorted(hosts))
                melde(B, "keine Cookies (%s)" % tag, not kekse and not speicher["cookie"], "kritisch", "context.cookies(), document.cookie", [c["name"] for c in kekse])
                melde(B, "keine Fremdskripte (%s)" % tag, not skripte, "kritisch", "Mitschnitt script-Anfragen", sorted(skripte)[:3])
                erwartet_ls = {"investtimer-sitzung", "investtimer-aktuell", "investtimer-lang", "investtimer-hinweis"} if ein else set()
                melde(B, "Speicher (%s): localStorage %s, sessionStorage %s, IndexedDB %s, Cache %s" % (tag, speicher["ls"], speicher["ss"], speicher["idb"], speicher["caches"]),
                      ein or not speicher["ls"], "mittel" if not ein else "info", "localStorage/sessionStorage/IndexedDB/Cache Storage")
                await ctx.close()
        await b.close()
    return texte


def ki_stichproben():
    """10 echte Antworten ueber die eigene Testinstanz (Port 8198, eigene ki.db, Beispielfragen aus dem Tages-Cache)."""
    subprocess.run(["bash", str(ROOT / "tests" / "ki_instanz.sh"), "stop"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    log = AUSGABE / "ki_instanz_start.log"
    with open(log, "w") as f:
        subprocess.run(["bash", str(ROOT / "tests" / "ki_instanz.sh"), "start"], stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, timeout=300)
    if "bereit" not in log.read_text():
        melde(B, "KI-Testinstanz startet", False, "mittel", "tests/ki_instanz.sh", log.read_text()[-200:])
        return []
    fragen = [("Was bedeutet der heutige Wert?", "de"), ("Was bewegt den Wert gerade?", "de"), ("Wie nervös ist der Markt im Moment?", "de"),
              ("Wie sah es im Corona-Crash 2020 aus?", "de"), ("Wie lange dauern Stressphasen meistens?", "de"), ("Soll ich jetzt kaufen?", "de"),
              ("Ist das ein guter Zeitpunkt zum Einsteigen?", "de"), ("Welche Aktien soll ich verkaufen?", "de"), ("Is now a good time to buy stocks?", "en"),
              ("What does today’s reading mean?", "en")]
    aus = []
    try:
        for i, (f, sp) in enumerate(fragen):
            req = urllib.request.Request("http://127.0.0.1:8198/v1/investtimer/chat", data=json.dumps({"frage": f, "verlauf": [], "sprache": sp}).encode(),
                                         headers={"Content-Type": "application/json", "X-Real-IP": "10.77.%d.%d" % (int(time.time()) % 200, i)})
            try:
                a = json.load(urllib.request.urlopen(req, timeout=180)).get("antwort", "")
            except Exception as e:
                a = ""
                melde(B, "KI-Antwort erhalten: %s" % f, False, "mittel", "Testinstanz", str(e)[:120])
            aus.append({"frage": f, "antwort": a})
    finally:
        subprocess.run(["bash", str(ROOT / "tests" / "ki_instanz.sh"), "stop"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    (AUSGABE / "ki_stichproben.json").write_text(json.dumps(aus, ensure_ascii=False, indent=1))
    return aus


def main():
    k = None
    try:
        k = testkonto()
        texte = asyncio.run(mitschnitt(k))
    except Exception as e:
        melde(B, "Mitschnitt durchgelaufen", False, "hoch", "tests/qa/datenschutz.py", "%s: %s" % (type(e).__name__, e))
        texte = {}
    finally:
        aufraeumen()
    for name, t in texte.items():
        sprache_pruefen("Seite " + name, t)
        if name.startswith("aus"):
            quellen_pruefen("Seite " + name, t)
    for pfad in ("/impressum.html", "/datenschutz.html"):
        _, h, _ = http("GET", pfad)
        t = re.sub(r"<[^>]+>", " ", str(h))
        sprache_pruefen(pfad, t, "mittel")
        if pfad == "/impressum.html":
            melde(B, "Impressum mit Strasse, PLZ/Ort und E-Mail", bool(re.search(r"(stra(ß|ss)e|str\.|weg|platz|allee|gasse|ring)\s*\d+", t, re.I)) and bool(re.search(r"\b\d{5}\s+[A-ZÄÖÜ]", t))
                  and "@investtimer.net" in t, "hoch", "/impressum.html", re.sub(r"\s+", " ", t)[:160])
    # Vorlagen: nur Texte, die Nutzer sehen (Zeichenketten ohne CSS/HTML/Code), vorbereitete KI-Antworten nur in den Antwortfeldern
    vorlagen_alle = ""
    for f in ("volafly-api/investtimer_alarme.py", "volafly-api/investtimer_api_alarm_mail.py", "server/push_senden.py", "tools/teilen.js",
              "volafly-api/investtimer_api_teilen.py", "server/teilen_bilder.py", "volafly-api/investtimer_vertrag.py", "server/og_bild.py"):
        p = ROOT / f
        if not p.exists():
            continue
        roh = [a or b for a, b in re.findall(r"'([^'\n]{12,})'|\"([^\"\n]{12,})\"", p.read_text(encoding="utf-8"))]
        texte_ = " | ".join(x for x in roh if not re.search(r"[{};<>]|px\b|\\d|https?://|\(\?|\[\^", x))
        sprache_pruefen("Vorlage " + f, texte_)
        quellen_pruefen("Vorlage " + f, texte_)
        vorlagen_alle += texte_
    faq = json.loads((ROOT / "tools" / "faq.json").read_text(encoding="utf-8"))
    faq_t = json.dumps(faq, ensure_ascii=False)
    sprache_pruefen("FAQ (DE/EN)", faq_t)
    quellen_pruefen("FAQ (DE/EN)", faq_t)
    ant = json.loads((ROOT / "volafly-api" / "investtimer_antworten.json").read_text(encoding="utf-8"))
    sichtbar = " | ".join(str(e.get(k, "")) for e in ant.get("antworten", []) + ant.get("vorlagen", [])
                          for k in ("antwort", "vorlage", "fehlende_daten", "bedingungssaetze", "teilvorlagen"))
    sprache_pruefen("vorbereitete KI-Antworten", sichtbar)
    quellen_pruefen("vorbereitete KI-Antworten", sichtbar)
    for s in ki_stichproben():
        sprache_pruefen("KI-Antwort auf „%s“" % s["frage"], s["antwort"])
        quellen_pruefen("KI-Antwort auf „%s“" % s["frage"], s["antwort"])
    return ende()


if __name__ == "__main__":
    sys.exit(main())
