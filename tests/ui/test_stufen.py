"""Fuenf Stufen: Testwerte 15/30/50/70/90 (angemeldet), Label sichtbar, Farben, Bogen faerbt sich beim Fuellen, reduzierte Bewegung."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
ERW = {15: ('Ruhig', '#2e6b57'), 30: ('Moderat', '#6f7f45'), 50: ('Erhöht', '#a0722f'), 70: ('Hoch', '#a24524'), 90: ('Panik', '#8e2a27')}
def rgb(h): return 'rgb(%d, %d, %d)' % tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for wert, (label, farbe) in ERW.items():
            harness.ZUSTAND['wert'] = wert
            ctx = await b.new_context(viewport={'width': 390, 'height': 760}, device_scale_factor=2)
            await harness.supabase_route(ctx)
            pg = await ctx.new_page()
            await pg.goto(url + harness.LOGIN_HASH)
            await pg.wait_for_function("w=>document.querySelector('.score').textContent.trim()===String(w)", arg=wert, timeout=9000)
            await pg.wait_for_timeout(2400)
            r = await pg.evaluate("""()=>({status:document.querySelector('#status').textContent,statusSichtbar:document.querySelector('#status').getBoundingClientRect().height>0,
              bogen:getComputedStyle(document.querySelector('.gauge-value')).stroke,punkt:getComputedStyle(document.querySelector('.gauge-point')).fill,
              zahl:getComputedStyle(document.querySelector('.score')).color,statusFarbe:getComputedStyle(document.querySelector('#status')).color})""")
            pruefe(r['status'] == label and r['statusSichtbar'], f'{wert}: Label {r["status"]}')
            pruefe(r['bogen'] == rgb(farbe) and r['punkt'] == rgb(farbe), f'{wert}: Bogen/Punkt {r["bogen"]}')
            pruefe(r['zahl'] == 'rgb(27, 51, 48)', f'{wert}: grosse Zahl dunkel ({r["zahl"]})')
            if SHOT: await pg.locator('.score-column').screenshot(path=str(SHOT / f'stufe_{wert}.png'))
            await ctx.close()
        # Fuellen: Zwischenfarbe zwischen ruhig und Ziel, reduzierte Bewegung sofort Ziel
        harness.ZUSTAND['wert'] = 90
        ctx = await b.new_context(viewport={'width': 390, 'height': 760}); await harness.supabase_route(ctx)
        pg = await ctx.new_page(); await pg.goto(url + harness.LOGIN_HASH)
        farben = set()
        for _ in range(40):
            farben.add(await pg.evaluate("getComputedStyle(document.querySelector('.gauge-value')).stroke")); await pg.wait_for_timeout(60)
        pruefe(len(farben) > 5 and rgb('#8e2a27') in farben, f'Fuellen: {len(farben)} Farbstufen bis zur Zielfarbe')
        await ctx.close()
        ctx = await b.new_context(viewport={'width': 390, 'height': 760}, reduced_motion='reduce'); await harness.supabase_route(ctx)
        pg = await ctx.new_page(); await pg.goto(url + harness.LOGIN_HASH)
        await pg.wait_for_function("document.querySelector('.score').textContent.trim()==='90'", timeout=9000)
        f = await pg.evaluate("getComputedStyle(document.querySelector('.gauge-value')).stroke")
        pruefe(f == rgb('#8e2a27'), f'reduzierte Bewegung: sofort Zielfarbe {f}')
        await ctx.close()
        harness.ZUSTAND['wert'] = None
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
