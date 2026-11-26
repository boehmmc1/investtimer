"""Block E (25.11.2026): Fehlt der Bogen (.gauge-stage) im DOM, bricht die Seite nicht ab: kein JS-Fehler, Sprachwechsel und
Aktualisierung laufen weiter, genau eine Meldung "Anzeige fehlt im DOM" mit Umfeld (ohne Personenbezug). Normaler Aufruf meldet nichts."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)

async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for ein in (False, True):
            for w in (390, 1280):
                tag = f'{w} {"ein" if ein else "aus"}'
                harness.ZUSTAND['fehler'].clear()
                ctx = await b.new_context(viewport={'width': w, 'height': 844}, is_mobile=w < 760, has_touch=w < 760)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                pg.on('console', lambda m: js.append(m.text) if m.type == 'error' else None)
                await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(2500)
                pruefe(not js and not harness.ZUSTAND['fehler'], f'{tag}: normaler Aufruf ohne Fehler und ohne Meldung {js} {harness.ZUSTAND["fehler"]}')
                await pg.evaluate("document.querySelector('.gauge-stage').remove()")
                await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}")
                await pg.wait_for_timeout(600)
                summary = await pg.evaluate("document.querySelector('#summary')?.textContent||''")
                pruefe(document_en := ('stress' in summary.lower() or 'market' in summary.lower()), f'{tag}: Sprachwechsel laeuft weiter ("{summary[:40]}")')
                await pg.evaluate("document.dispatchEvent(new Event('investtimer:update'))"); await pg.wait_for_timeout(400)
                await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='de';h.dispatchEvent(new Event('change',{bubbles:true}))}")
                await pg.wait_for_timeout(1200)
                pruefe(await pg.evaluate("document.documentElement.lang") == 'de', f'{tag}: zurueck auf Deutsch')
                pruefe(not js, f'{tag}: ohne Bogen keine JS-Fehler {js[:3]}')
                m = [f for f in harness.ZUSTAND['fehler'] if f.get('meldung') == 'Anzeige fehlt im DOM']
                pruefe(len(m) == 1 and len(harness.ZUSTAND['fehler']) == 1, f'{tag}: genau eine Meldung "Anzeige fehlt im DOM" ({len(harness.ZUSTAND["fehler"])})')
                u = m[0].get('umfeld', {}) if m else {}
                pruefe(u.get('stage') == 0 and u.get('webdriver') in ('ja', 'nein') and u.get('sichtbar') == 'visible' and set(u) == {'score', 'stage', 'uebersetzt', 'erweiterung', 'webdriver', 'sichtbar', 'ref'},
                       f'{tag}: Umfeld ohne Personenbezug {u}')
                await ctx.close()
        await b.close()
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
