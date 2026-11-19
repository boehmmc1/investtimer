"""Layoutspruenge (CLS) beim Laden, Fehler- und Leerzustaende (Verlauf, Alarme, Konto), Tastaturbedienung der Tabs."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
CLS = "window.__cls=0;new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__cls+=e.value}).observe({type:'layout-shift',buffered:true})"
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in ((390, 844), (1280, 860)):
            for ein in (False, True):
                ctx = await br.new_context(viewport={'width': w, 'height': h}); await harness.supabase_route(ctx)
                await ctx.add_init_script(CLS)
                pg = await ctx.new_page(); await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(2500)
                cls = await pg.evaluate("window.__cls")
                pruefe(cls < 0.1, f'{w} {"ein" if ein else "aus"}: Layoutspruenge beim Laden CLS={cls:.3f}')
                await ctx.close()
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}); await harness.supabase_route(ctx)
        pg = await ctx.new_page()
        await pg.route('**/api/historie', lambda r: r.fulfill(status=503, json={'error': 'unavailable'}))
        await pg.route('**/api/alarme', lambda r: r.fulfill(status=503, json={'error': 'unavailable'}))
        await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1200)
        await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1200)
        t = await pg.evaluate("document.querySelector('#verlauf-ansicht').innerText")
        pruefe('gerade nicht verfügbar' in t, 'Verlauf-Fehler: freundliche Meldung')
        await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(1200)
        t = await pg.evaluate("document.querySelector('#konto-ansicht').innerText")
        pruefe('nicht geklappt' in t, 'Alarme-Fehler in der Konto-Ansicht: freundliche Meldung')
        await pg.unroute('**/api/alarme')
        harness.ZUSTAND['alarme'] = {'alarme': [], 'geraete': 0, 'max': 5, 'vapid': 'x', 'email': harness.EMAIL}
        await pg.goto('about:blank'); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1000); await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(1000)
        t = await pg.evaluate("document.querySelector('#konto-ansicht').innerText")
        pruefe('Noch kein Alarm angelegt' in t, 'Leerzustand Alarme')
        harness.ZUSTAND['alarme'] = None
        await ctx.close()
        # Tastatur: Tabs per Tab-Taste erreichbar, Enter wechselt die Ansicht, Fokus sichtbar
        ctx = await br.new_context(viewport={'width': 1280, 'height': 860}); await harness.supabase_route(ctx)
        pg = await ctx.new_page(); await pg.goto(url); await pg.wait_for_timeout(1200)
        erreicht = None
        for i in range(12):
            await pg.keyboard.press('Tab')
            z = await pg.evaluate("document.activeElement?.dataset?.ziel||null")
            if z == 'verlauf': erreicht = i; break
        ring = await pg.evaluate("getComputedStyle(document.activeElement).outlineStyle")
        pruefe(erreicht is not None and ring != 'none', f'Tastatur: Tab "Verlauf" nach {erreicht} Tabs erreicht, Fokusrahmen {ring}')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1200)
        pruefe(await pg.evaluate("location.hash") == '#verlauf', 'Tastatur: Enter oeffnet den Verlauf')
        await ctx.close(); await br.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
