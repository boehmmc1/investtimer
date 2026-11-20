"""Block 11: FAQ (#faq) mit Akkordeon/Tastatur/Strukturdaten, Aktualitaetszeile (Aktualisiert / Nicht aktualisiert · Stand, Abruf fehlgeschlagen, ausgeloggt),
Fehlererfassung im Browser, Zaehlaufruf je Ansicht ohne Kennung. Screenshots nach <ordner>."""
import asyncio, sys, json, datetime
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
        # FAQ
        for w, h in ((320, 640), (390, 844), (1280, 860)):
            for sp in ('de', 'en'):
                ctx = await br.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=2 if SHOT else 1)
                pg = await ctx.new_page(); js = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                await pg.goto(url); await pg.wait_for_timeout(900)
                if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
                await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(500)
                await pg.click('[data-konto=faq]'); await pg.wait_for_timeout(500)
                r = await pg.evaluate("({hash:location.hash,n:document.querySelectorAll('.faq-frage').length,offen:document.querySelectorAll('.faq-antwort:not([hidden])').length,titel:document.title})")
                pruefe(r['hash'] == '#faq' and r['n'] == 12 and r['offen'] == 1 and ('Häufige Fragen' in r['titel'] or 'FAQ' in r['titel']), f'FAQ {w} {sp}: {r}')
                b = await pg.evaluate(PRUEF, {'bereich': 'oben'})
                pruefe(not b, f'FAQ {w} {sp}: nichts abgeschnitten/ueberdeckt {b[:3]}')
                if SHOT and sp == 'de' and w != 1280: await pg.screenshot(path=str(SHOT / f'faq_{w}_erste_offen.png'))
                await pg.focus('#faq-f0'); await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
                r = await pg.evaluate("({fokus:document.activeElement.id,offen:[...document.querySelectorAll('.faq-antwort:not([hidden])')].map(x=>x.id)})")
                pruefe(r['fokus'] == 'faq-f2' and r['offen'] == ['faq-a2'], f'FAQ {w} {sp}: Tastatur, nur eine Frage offen {r}')
                await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
                pruefe(await pg.evaluate("document.querySelectorAll('.faq-antwort:not([hidden])').length") == 0, f'FAQ {w} {sp}: zuklappen')
                if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / f'faq_{w}_zu.png'), full_page=True)
                t = await pg.evaluate("document.querySelector('#faq-ansicht').innerText")
                for k in ('VIX', 'S&P', '%', 'Gewicht', 'kostet', 'Testphase', 'Widerruf'):
                    pruefe(k not in t, f'FAQ {w} {sp}: kein "{k}"')
                pruefe(not js, f'FAQ {w} {sp}: keine JS-Fehler {js}')
                await ctx.close()
        # Aktualitaet: zwei Zustaende (Aktualisiert / Nicht aktualisiert · Stand), Grenze 45 Min., auch am Wochenende
        faelle = [('frisch', '2026-11-18T16:00:00Z', 4, 'de', 'Aktualisiert', 'ok'),
                  ('wochenende', '2026-11-22T12:00:00Z', 20, 'de', 'Aktualisiert', 'ok'),
                  ('grenze', '2026-11-18T16:00:00Z', 44, 'de', 'Aktualisiert', 'ok'),
                  ('alt', '2026-11-18T17:00:00Z', 75, 'de', 'Nicht aktualisiert · Stand 18. Nov. 2026, 16:45', 'alt'),
                  ('alt_en', '2026-11-18T17:00:00Z', 75, 'en', 'Not updated · as of Nov 18, 2026, 16:45', 'alt'),
                  ('frisch_en', '2026-11-18T16:00:00Z', 4, 'en', 'Up to date', 'ok'),
                  ('abruf_fehlgeschlagen', '2026-11-18T16:00:00Z', 4, 'de', 'Nicht aktualisiert · Stand 18. Nov. 2026, 16:56', 'alt')]
        for name, uhr, alter, sp, erwartet, punkt in faelle:
            harness.ZUSTAND['alter_min'] = alter
            ctx = await br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2 if SHOT else 1); await harness.supabase_route(ctx)
            pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            await pg.clock.install(time=datetime.datetime.fromisoformat(uhr.replace('Z', '+00:00')))
            await pg.clock.resume()
            await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(2500)
            if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
            # berechnetUm relativ zur simulierten Uhr setzen
            await pg.evaluate("a=>{const v=window.InvestTimer.live;v.berechnetUm=new Date(Date.now()-a*60000).toISOString();window.InvestTimer.gespeichert=v;window.InvestTimer.aktualitaet()}", alter)
            if name == 'abruf_fehlgeschlagen':
                await pg.route('**/api/aktuell', lambda r: r.fulfill(status=503, body='{}'))
                await pg.evaluate("window.InvestTimer.loadLive(true)"); await pg.wait_for_timeout(1200)
            t = await pg.evaluate("document.querySelector('.snapshot-label').textContent")
            pk = await pg.evaluate("(()=>{const s=document.querySelector('.aktualitaet-punkt');return s?[s.classList.contains('ok')?'ok':'alt',getComputedStyle(s).backgroundColor]:null})()")
            pruefe(t.strip() == erwartet and pk and pk[0] == punkt and not any(k in t for k in ('Min.', 'min', 'Börse', 'market')), f'Aktualitaet {name}: "{t}" {pk}')
            pruefe(not js, f'Aktualitaet {name}: keine JS-Fehler {js}')
            if SHOT: await pg.locator('.score-column').screenshot(path=str(SHOT / f'aktualitaet_{name}.png'))
            await ctx.close()
        harness.ZUSTAND['alter_min'] = 3
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}); pg = await ctx.new_page()
        await pg.goto(url); await pg.wait_for_timeout(1500)
        t = await pg.evaluate("document.querySelector('.snapshot-label').textContent")
        pruefe(t.startswith('Zeitversetzter Stand'), f'Aktualitaet ausgeloggt unveraendert: "{t}"')
        # Zaehlaufruf und Fehlererfassung
        harness.ZUSTAND['ansichten'].clear(); harness.ZUSTAND['fehler'].clear()
        await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(600)
        await pg.evaluate("setTimeout(()=>{throw new Error('Testfehler 11 aus dem Browser')},0)"); await pg.wait_for_timeout(800)
        await pg.evaluate("()=>{Promise.reject(new Error('Testablehnung'));return 1}"); await pg.wait_for_timeout(800)
        a = harness.ZUSTAND['ansichten']; f = harness.ZUSTAND['fehler']
        pruefe(any('a=verlauf' in x and 'l=de' in x and ('g=mobil' in x or 'g=desktop' in x) for x in a) and all('@' not in x for x in a), f'Zaehlaufruf ohne Kennung {a}')
        pruefe(any('Testfehler 11' in x['meldung'] and x['ansicht'] == 'verlauf' and x['version'] for x in f) and any('Testablehnung' in x['meldung'] for x in f), f'Fehler erfasst: {[x["meldung"] for x in f]}')
        pruefe(all('@' not in json.dumps(x) for x in f), 'Fehlermeldung ohne E-Mail')
        st = await pg.evaluate("[document.cookie, localStorage.length]")
        pruefe(st == ['', 0], f'ausgeloggt: keine Cookies, kein localStorage {st}')
        await ctx.close(); await br.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
