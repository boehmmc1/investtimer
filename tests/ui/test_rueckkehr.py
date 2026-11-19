"""Rueckkehr in die installierte App: Wert serverseitig aendern, App 'aus dem Hintergrund' holen (visibilitychange, pageshow,
focus, online) -> neuer Wert innerhalb von 3 s, ohne Neuladen der Seite; offene Ansicht (Verlauf) wird neu geholt; Ladepunkt."""
import asyncio, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
SICHTBAR = "v=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>v});Object.defineProperty(document,'hidden',{configurable:true,get:()=>v!=='visible'});document.dispatchEvent(new Event('visibilitychange'))}"
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True); await harness.supabase_route(ctx)
        pg = await ctx.new_page()
        harness.ZUSTAND.update(wert=50)
        await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(2500)
        await pg.evaluate("window.__marke=1")
        for ereignis, wert in (('visibilitychange', 57), ('pageshow', 62), ('focus', 44), ('online', 71)):
            await pg.evaluate(SICHTBAR, 'hidden'); await pg.wait_for_timeout(300)
            harness.ZUSTAND['wert'] = wert
            t0 = time.time()
            if ereignis == 'visibilitychange': await pg.evaluate(SICHTBAR, 'visible')
            elif ereignis == 'pageshow': await pg.evaluate(SICHTBAR + ";", 'visible') if False else await pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))}")
            elif ereignis == 'focus': await pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});dispatchEvent(new Event('focus'))}")
            else: await pg.evaluate("()=>{Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});dispatchEvent(new Event('online'))}")
            ok = False
            for _ in range(30):
                if await pg.evaluate("document.querySelector('.gauge-stage .score').textContent.trim()") == str(wert): ok = True; break
                await pg.wait_for_timeout(100)
            dauer = time.time() - t0
            await pg.wait_for_timeout(2100)  # Entprellung 2 s zwischen zwei Rueckkehr-Ereignissen
            pruefe(ok and dauer < 3 and await pg.evaluate("window.__marke===1"), f'{ereignis}: neuer Wert {wert} nach {dauer:.1f} s, ohne Neuladen')
        # offene Ansicht Verlauf wird neu geholt
        await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
        harness.ZUSTAND['aufrufe'].clear()
        await pg.evaluate(SICHTBAR, 'hidden'); await pg.wait_for_timeout(2100); await pg.evaluate(SICHTBAR, 'visible'); await pg.wait_for_timeout(1200)
        geholt = [a[1] for a in harness.ZUSTAND['aufrufe']]
        pruefe('/api/historie' in geholt and '/api/aktuell' in geholt and '/sw.js' in geholt or ('/api/historie' in geholt and '/api/aktuell' in geholt), f'Verlauf offen: Wert und Verlauf neu geholt {sorted(set(geholt))}')
        # Ladepunkt an der Stand-Zeile (waehrend des Ladens)
        harness.ZUSTAND['aktuell_verzoegerung'] = 1.5
        await pg.evaluate("location.hash=''"); await pg.wait_for_timeout(500)
        await pg.evaluate(SICHTBAR, 'hidden'); await pg.wait_for_timeout(2100); await pg.evaluate(SICHTBAR, 'visible'); await pg.wait_for_timeout(300)
        punkt = await pg.evaluate("getComputedStyle(document.querySelector('.snapshot-label'),'::after').content")
        breite_vor = await pg.evaluate("document.querySelector('.snapshot-label').getBoundingClientRect().width")
        await pg.wait_for_timeout(1800)
        breite_nach = await pg.evaluate("document.querySelector('.snapshot-label').getBoundingClientRect().width")
        pruefe(punkt not in ('none', 'normal') and abs(breite_vor - breite_nach) < 0.5, f'Ladepunkt sichtbar, kein Sprung der Stand-Zeile ({punkt}, {breite_vor:.1f}->{breite_nach:.1f})')
        harness.ZUSTAND.update(aktuell_verzoegerung=0, wert=None)
        await ctx.close(); await br.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
