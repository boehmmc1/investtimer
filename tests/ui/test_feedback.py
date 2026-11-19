"""Feedback (#feedback): Einstiege (Konto-Ansicht, Fusszeile), Formular, Pflichtfelder, Mindestzeit, Honeypot-Feld unsichtbar,
E-Mail vorbelegt (eingeloggt), Versand, Bestaetigung, Fehlerfaelle; Screenshots leer/ausgefuellt/Bestaetigung."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
PRUEF = (Path(__file__).parent / 'pruefen.js').read_text()
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in ((320, 640), (390, 844), (1280, 860)):
            for ein in (False, True):
                for sp in ('de', 'en'):
                    harness.ZUSTAND.update(feedback_status=200, feedback=[])
                    ctx = await br.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=2 if SHOT else 1)
                    await harness.supabase_route(ctx)
                    pg = await ctx.new_page(); js = []
                    pg.on('pageerror', lambda e: js.append(str(e)))
                    await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1000)
                    if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
                    tag = f'{w} {"ein" if ein else "aus"} {sp}'
                    pruefe(await pg.evaluate("[...document.querySelectorAll('.app-footer a')].some(a=>a.getAttribute('href')==='#feedback'&&a.offsetParent)") or w < 760, f'{tag}: Fusszeile mit Link Feedback')
                    await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(700)
                    await pg.click('[data-konto=feedback]'); await pg.wait_for_timeout(600)
                    pruefe(await pg.evaluate("location.hash") == '#feedback', f'{tag}: Konto -> Feedback geben oeffnet #feedback')
                    r = await pg.evaluate("""()=>({titel:document.querySelector('#feedback-titel')?.textContent,chips:document.querySelectorAll('.feedback-chip').length,mail:document.querySelector('#feedback-email')?.value,
                       hp:(()=>{const e=document.querySelector('#feedback-website').getBoundingClientRect();return e.right<0||e.width<=1})()})""")
                    pruefe(r['chips'] == 4 and r['hp'] and (r['mail'] == harness.EMAIL) == ein and r['titel'] in ('Was können wir besser machen?', 'What can we do better?'), f'{tag}: Formular {r}')
                    befunde = await pg.evaluate(PRUEF, {'bereich': 'oben'})
                    pruefe(not befunde, f'{tag}: nichts abgeschnitten/ueberdeckt {befunde[:3]}')
                    if SHOT and sp == 'de' and ein: await pg.screenshot(path=str(SHOT / f'feedback_leer_{w}.png'), full_page=True)
                    await pg.click('.feedback-absenden'); await pg.wait_for_timeout(200)
                    m = await pg.evaluate("document.querySelector('#feedback-meldung').textContent")
                    pruefe(bool(m) and not harness.ZUSTAND['feedback'], f'{tag}: leeres Formular -> Hinweis "{m[:40]}", nichts gesendet')
                    await pg.click('.feedback-chip[data-art=fehler]'); await pg.fill('#feedback-text', 'Testnachricht: Im Verlauf fehlt bei 320 px nichts, alles gut lesbar.')
                    z = await pg.evaluate("document.querySelector('#feedback-zaehler').textContent")
                    pruefe(z.startswith('68 /'), f'{tag}: Zeichenzaehler {z}')
                    if SHOT and sp == 'de' and ein: await pg.screenshot(path=str(SHOT / f'feedback_ausgefuellt_{w}.png'), full_page=True)
                    await pg.wait_for_timeout(2600)
                    await pg.click('.feedback-absenden'); await pg.wait_for_timeout(700)
                    gesendet = harness.ZUSTAND['feedback'][-1] if harness.ZUSTAND['feedback'] else {}
                    pruefe(gesendet.get('kategorie') == 'fehler' and gesendet.get('dauer', 0) >= 3000 and gesendet.get('website') == '' and gesendet.get('version') and gesendet.get('ansicht') == 'konto', f'{tag}: Versand mit Kategorie, Dauer, leerem Honeypot, Version, Ansicht {dict((k, gesendet.get(k)) for k in ("kategorie", "dauer", "ansicht", "version", "sprache"))}')
                    t = await pg.evaluate("document.querySelector('#feedback-titel')?.textContent")
                    pruefe(t in ('Danke! Deine Nachricht ist angekommen.', 'Thanks! Your message has arrived.'), f'{tag}: Bestaetigung "{t}"')
                    if SHOT and sp == 'de' and ein: await pg.screenshot(path=str(SHOT / f'feedback_bestaetigung_{w}.png'))
                    await pg.click('[data-fb=zurueck]'); await pg.wait_for_timeout(500)
                    pruefe(await pg.evaluate("location.hash") == '#konto', f'{tag}: Zurueck fuehrt zur Konto-Ansicht')
                    # Fehlerfaelle
                    for st, wort in ((502, 'info@investtimer.net'), (429, 'info@investtimer.net')):
                        harness.ZUSTAND['feedback_status'] = st
                        await pg.evaluate("location.hash='feedback'"); await pg.wait_for_timeout(400)
                        await pg.click('.feedback-chip[data-art=idee]'); await pg.fill('#feedback-text', 'Noch eine Idee fuer die Seite.'); await pg.wait_for_timeout(3100)
                        await pg.click('.feedback-absenden'); await pg.wait_for_timeout(600)
                        m = await pg.evaluate("document.querySelector('#feedback-meldung')?.textContent||''")
                        pruefe(wort in m, f'{tag}: Fehler {st} -> "{m[:60]}"')
                    pruefe(not js, f'{tag}: keine JS-Fehler {js}')
                    await ctx.close()
        await br.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
