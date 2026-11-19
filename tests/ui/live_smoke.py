"""Kurzpruefung der Live-Seite im Browser (ausgeloggt): Wert, Ansichten #ki/#verlauf/#konto, keine JS-Fehler."""
import asyncio, sys
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'https://investtimer.net/'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        pg = await ctx.new_page(); js = []
        pg.on('pageerror', lambda e: js.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(2500)
        wert = await pg.evaluate("document.querySelector('.score')?.textContent.trim()")
        erg = {'wert': wert}
        for z in ('ki', 'verlauf', 'konto'):
            await pg.tap('.it-leiste [data-ziel=%s]' % z); await pg.wait_for_timeout(2000)
            erg[z] = await pg.evaluate("z=>{const e=document.querySelector('#'+z+'-ansicht');return !!e&&!e.hidden&&location.hash==='#'+z}", z)
        erg['verlauf_chart'] = await pg.evaluate("!!document.querySelector('#verlauf-ansicht svg.verlauf-svg')") if True else None
        erg['version'] = await pg.evaluate("document.querySelector('.konto-version')?.textContent")
        erg['js'] = js
        print(erg)
        ok = wert and wert.isdigit() and erg['ki'] and erg['verlauf'] and erg['konto'] and not js
        await b.close()
        return 0 if ok else 1
sys.exit(asyncio.run(main()))
