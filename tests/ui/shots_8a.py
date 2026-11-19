"""Screenshots Block 8a: Header-Tabs (1024/1280/1440, DE/EN), Startseite mit KI-Bruecke (1280/390, ein/aus), Ereigniskarte, KI-Tab mit Herkunft."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
Z = Path(sys.argv[1]); Z.mkdir(parents=True, exist_ok=True)
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w in (1024, 1280, 1440):
            for sp in ('de', 'en'):
                ctx = await b.new_context(viewport={'width': w, 'height': 800}, device_scale_factor=1); await harness.supabase_route(ctx)
                pg = await ctx.new_page(); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1500)
                if sp == 'en': await pg.select_option('#header-language', 'en'); await pg.wait_for_timeout(300)
                await pg.screenshot(path=str(Z / f'header_{w}_{sp}.png'), clip={'x': 0, 'y': 0, 'width': w, 'height': 120})
                await ctx.close()
        for w, h in ((1280, 860), (390, 844)):
            for ein in (False, True):
                ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if w < 900 else 1, is_mobile=w < 900, has_touch=w < 900); await harness.supabase_route(ctx)
                pg = await ctx.new_page(); await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(2600)
                t = f'{w}_{"ein" if ein else "aus"}'
                await pg.screenshot(path=str(Z / f'start_{t}.png'), full_page=(w > 900))
                await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
                k = pg.locator('#verlauf-ansicht .ereignis-karte'); await k.scroll_into_view_if_needed(); await k.screenshot(path=str(Z / f'ereigniskarte_{t}.png'))
                await pg.click('.ereignis-karte .ki-bruecke'); await pg.wait_for_timeout(1200)
                await pg.screenshot(path=str(Z / f'ki_kontext_phase_{t}.png'))
                await ctx.close()
        await b.close()
asyncio.run(main())
