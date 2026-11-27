"""KI-Limit in der Oberflaeche: Hinweiszeile vor Verbrauch, nach Verbrauch Eingabe gesperrt mit Text, Beispielfragen und
Folgefragen klickbar (senden direkt), Zustand "ausgelastet", Englisch, keine Zaehler. Screenshots nach <ordner>."""
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
TEXT = {'de': ('1 freie Frage heute · KI, keine Anlageberatung', 'Heutige freie Frage genutzt · KI, keine Anlageberatung',
               'KI für heute ausgelastet · keine Anlageberatung'),
        'en': ('1 free question today · AI, not investment advice', 'Today’s free question used · AI, not investment advice',
               'AI at capacity today · not investment advice')}  # Block J3 (25.11.2026): eine Zeile mit Info-Symbol
AUS_MELDUNG = {'de': 'Die KI ist für heute ausgelastet. Die Beispielfragen funktionieren weiter.', 'en': 'The AI is at capacity for today. The example questions still work.'}
ZUSTAND_JS = """()=>{const i=document.querySelector('#ki-eingabe'),l=document.querySelector('#ki-limit span');
 return {gesperrt:i?i.disabled:null,limit:l?l.textContent:'',text:document.querySelector('#ki-ansicht').innerText,
  hervor:document.querySelector('#ki-ansicht').classList.contains('ki-frei-leer')}}"""
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in ((390, 844), (1280, 860)):
            for sp in ('de', 'en'):
                harness.ZUSTAND.update(chat_status=200, frei={'verbraucht': False, 'ausgelastet': False}, antwort=None)
                ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=2 if SHOT else 1)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                pg.on('console', lambda m: js.append(m.text) if m.type == 'error' and 'status of 429' not in m.text else None)
                await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1200)
                if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
                await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(900)
                tag = f'{w} {sp}'
                z = await pg.evaluate(ZUSTAND_JS)
                pruefe(z['limit'] == TEXT[sp][0] and z['gesperrt'] is False and not z['hervor'], f'{tag}: vor Verbrauch Hinweiszeile, Eingabe frei "{z["limit"]}"')
                if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / f'ki_vorher_{w}.png'))
                # freie Frage stellen: Antwort meldet "verbraucht"
                harness.ZUSTAND['frei'] = {'verbraucht': True, 'ausgelastet': False}
                await pg.fill('#ki-eingabe', 'Eine eigene Frage'); await pg.press('#ki-eingabe', 'Enter'); await pg.wait_for_timeout(1200)
                z = await pg.evaluate(ZUSTAND_JS)
                pruefe(z['gesperrt'] is True and z['limit'] == TEXT[sp][1] and z['hervor'], f'{tag}: nach Verbrauch Eingabe gesperrt mit Text')
                pruefe('Noch' not in z['text'] and ' left' not in z['text'] and '0 Fragen' not in z['text'], f'{tag}: keine Zaehler')
                # Folgefrage-Chip sendet direkt
                n = await pg.evaluate("document.querySelectorAll('.ki-antwort').length")
                chip = pg.locator('.ki-chip').first
                pruefe(await chip.count() > 0 and await chip.is_enabled(), f'{tag}: Folgefrage-Chip klickbar')
                await chip.click(); await pg.wait_for_timeout(1200)
                pruefe(await pg.evaluate("document.querySelectorAll('.ki-antwort').length") == n + 1, f'{tag}: Chip sendet direkt trotz gesperrter Eingabe')
                if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / f'ki_nachher_gespraech_{w}.png'))
                # Startansicht: Karten hervorgehoben und klickbar
                await pg.click('[data-ki=neu]'); await pg.wait_for_timeout(500)
                z = await pg.evaluate(ZUSTAND_JS)
                farbe = await pg.evaluate("getComputedStyle(document.querySelector('.ki-gruppe .ki-frage')).color")
                pruefe(z['hervor'] and z['gesperrt'] is True, f'{tag}: Karten hervorgehoben ({farbe})')
                if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / f'ki_nachher_{w}.png'))
                if SHOT and sp == 'en': await pg.screenshot(path=str(SHOT / f'ki_nachher_{w}_en.png'))
                await pg.locator('.ki-gruppe .ki-frage').first.click(); await pg.wait_for_timeout(1200)
                pruefe(await pg.evaluate("document.querySelectorAll('.ki-antwort').length") == 1, f'{tag}: Karte sendet direkt')
                # Gesamtbremse: 429 ausgelastet
                harness.ZUSTAND.update(frei={'verbraucht': False, 'ausgelastet': False})
                await pg.goto('about:blank'); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1000)
                if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
                await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(800)
                harness.ZUSTAND.update(chat_status=429, chat_fehler='ausgelastet')
                await pg.fill('#ki-eingabe', 'Noch eine eigene Frage'); await pg.press('#ki-eingabe', 'Enter'); await pg.wait_for_timeout(1000)
                z = await pg.evaluate(ZUSTAND_JS)
                fm = await pg.evaluate("[...document.querySelectorAll('.ki-fehler')].pop()?.innerText||''")
                pruefe(z['gesperrt'] is True and z['limit'] == TEXT[sp][2] and AUS_MELDUNG[sp] in fm, f'{tag}: ausgelastet: Meldung und gesperrte Eingabe')
                harness.ZUSTAND.update(chat_status=200, chat_fehler='limit')
                # Zustand aus dem Konto beim Laden (ohne Frage)
                harness.ZUSTAND['frei'] = {'verbraucht': True, 'ausgelastet': False}
                await pg.goto('about:blank'); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1000)
                await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(900)
                z = await pg.evaluate(ZUSTAND_JS)
                pruefe(z['gesperrt'] is True, f'{tag}: verbraucht schon beim Oeffnen (aus /api/konto)')
                pruefe(not js, f'{tag}: keine JS-/Konsolenfehler {js[:3]}')
                await ctx.close()
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
