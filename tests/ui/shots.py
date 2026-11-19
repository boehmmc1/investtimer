"""Screenshots: python tests/ui/shots.py <zielordner> [public-ordner]"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
ZIEL = Path(sys.argv[1]); ZIEL.mkdir(parents=True, exist_ok=True)
QUELLE = Path(sys.argv[2]) if len(sys.argv) > 2 else harness.PUBLIC

async def main():
    srv, url = harness.starten(QUELLE)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in ((390, 844), (1280, 860)):
            for ein in (False, True):
                ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=w < 900, has_touch=w < 900)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page()
                fehler = []
                pg.on('pageerror', lambda e: fehler.append(str(e)))
                await pg.goto(url + (harness.LOGIN_HASH if ein else ''))
                await pg.wait_for_timeout(1800)
                tag = '%d_%s' % (w, 'ein' if ein else 'aus')
                await pg.screenshot(path=str(ZIEL / ('start_%s.png' % tag)), full_page=True)
                for hsh in ('ki', 'verlauf'):
                    await pg.evaluate("h=>location.hash=h", hsh)
                    await pg.wait_for_timeout(1500)
                    await pg.screenshot(path=str(ZIEL / ('%s_%s.png' % (hsh, tag))), full_page=False)
                if fehler:
                    print(tag, fehler)
                await ctx.close()
        await b.close()
asyncio.run(main())
