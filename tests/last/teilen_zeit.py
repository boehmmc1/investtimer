#!/usr/bin/env python3
"""Misst auf der Live-Seite die Zeit vom Tippen auf "Teilen" bis zum Teilen-Menue (navigator.share, nachgebildet) bzw. bis zum
offenen Dialog (Desktop) fuer Wert, Verlauf und Phase, ausgeloggt und eingeloggt (Testkonto, wird geloescht).
Aufruf: teilen_zeit.py <ausgabe.json>"""
import asyncio, json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "qa"))
os.environ.setdefault("QA_AUSGABE", "/var/lib/investtimer/last")
import gemeinsam as g
from playwright.async_api import async_playwright
SEITE = g.SEITE
MOCK = """window.__share=[];navigator.canShare=()=>true;navigator.share=d=>{window.__share.push({t:performance.now(),n:d.files&&d.files[0]&&d.files[0].size});return Promise.resolve()}"""
async def messen(b, ein, mobil, konto):
    ctx = await b.new_context(viewport={'width': 390, 'height': 844} if mobil else {'width': 1280, 'height': 860}, is_mobile=mobil, has_touch=mobil)
    pg = await ctx.new_page()
    if mobil: await pg.add_init_script(MOCK)
    if '--drossel' in sys.argv:   # Mobilfunk: 150 ms Latenz, 1,6 Mbit/s runter, 750 kbit/s hoch
        cdp = await ctx.new_cdp_session(pg)
        await cdp.send('Network.enable')
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 150, 'downloadThroughput': 200000, 'uploadThroughput': 93750})
    await pg.goto(SEITE + '/'); await pg.wait_for_timeout(1500)
    if ein:
        await pg.evaluate("([e,p])=>window.InvestTimer.mitPasswort(e,p)", [konto['email'], konto['passwort']]); await pg.reload(); await pg.wait_for_timeout(2500)
    aus = {}
    for art, vorher in (('wert', None), ('verlauf', "location.hash='verlauf'"), ('phase', None)):
        if vorher: await pg.evaluate(vorher); await pg.wait_for_timeout(2500)
        sel = {'wert': '.status-zeile .teilen-knopf, .teilen-start .teilen-knopf', 'verlauf': '.verlauf-kopf .teilen-knopf', 'phase': '.ereignis-karte .teilen-knopf'}[art]
        await pg.evaluate("document.querySelector('.teilen-dialog')?.close()")
        k = pg.locator(sel).first
        await k.scroll_into_view_if_needed(); await pg.wait_for_timeout(1500)
        n0 = await pg.evaluate("(window.__share||[]).length")
        t0 = await pg.evaluate("performance.now()")
        await k.click()
        try:
            if mobil:
                await pg.wait_for_function("n=>window.__share.length>n", arg=n0, timeout=40000)
                t1 = await pg.evaluate("window.__share[window.__share.length-1].t")
            else:
                await pg.wait_for_function("document.querySelector('.teilen-dialog')?.open&&document.querySelector('.teilen-dialog .teilen-bild')?.complete", timeout=40000)
                t1 = await pg.evaluate("performance.now()")
                await pg.evaluate("document.querySelector('.teilen-dialog')?.close()")
            aus[art] = round(t1 - t0)
        except Exception as e:
            aus[art] = 'Zeitueberschreitung (%s)' % ('Dialog statt Menue' if await pg.evaluate("!!document.querySelector('.teilen-dialog')?.open") else type(e).__name__)
        print(ein, mobil, art, aus[art], flush=True)
        await pg.evaluate("document.querySelector('.teilen-dialog')?.close()")
        await pg.wait_for_timeout(500)
    await ctx.close()
    return aus
async def main():
    k = g.testkonto()
    erg = {}
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=g.CHROME, args=['--no-sandbox'])
            for ein in (False, True):
                for mobil in (True, False):
                    erg['%s %s' % ('eingeloggt' if ein else 'ausgeloggt', 'Handy (navigator.share)' if mobil else 'Desktop (Dialog)')] = await messen(b, ein, mobil, k)
            await b.close()
    finally:
        g.aufraeumen()
    print(json.dumps(erg, ensure_ascii=False, indent=1))
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'): Path(sys.argv[1]).write_text(json.dumps(erg, ensure_ascii=False, indent=1))
asyncio.run(main())
