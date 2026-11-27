"""Nachtrag N2 (27.11.2026): Premium-Pflicht (IT_PREMIUM_PFLICHT=1) und freies Konto. Die API antwortet auf Premium-Pfaden mit
403 {"error":"premium"}. Das Frontend zeigt dann den ANGEMELDETEN Zustand mit Bezahlschranke: Avatar oben rechts, Konto erreichbar,
zeitversetzter Stand mit Hinweis "Mit Premium siehst du alles live." und Knopf "Premium ansehen" (oeffnet die Abo-Ansicht), nie
"Anmelden". Alarm, KI und Verlauf fuehren ebenfalls zur Abo-Ansicht. Mit Abo (kein 403): aktueller Wert, keine Schranke.
Chromium 390/1280 und WebKit iPhone 13, DE/EN, keine Konsolenfehler."""
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

ZUSTAND = """()=>{const l=document.querySelector('#account-login'),k=document.querySelector('[aria-controls=konto-menue]'),z=document.querySelector('#zeitversatz-zeile');
 return {member:InvestTimer.member,sperre:!!InvestTimer.premiumSperre,anmelden:!!(l&&l.offsetParent),avatar:!!(k&&k.offsetParent),
  zeile:!!(z&&!z.hidden&&z.offsetParent),zeileText:z?z.innerText.replace(/\\s+/g,' ').trim():'',wert:(document.querySelector('.score')||{}).textContent,
  pub:InvestTimer.pub&&InvestTimer.pub.rounded,paywall:!!document.querySelector('dialog[open]')&&/Premium/.test(document.querySelector('dialog[open]').innerText)}}"""

async def schliessen(pg):
    await pg.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())"); await pg.wait_for_timeout(200)

async def lauf(p, engine, geraet, w, sp):
    b = await (p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']) if engine == 'chromium' else p.webkit.launch())
    opt = dict(p.devices[geraet]) if geraet else dict(viewport={'width': w, 'height': 860 if w > 760 else 844}, is_mobile=w < 760, has_touch=w < 760)
    tag = f'{engine} {w} {sp}'
    for abo in (False, True):
        harness.ZUSTAND['pflicht'] = not abo
        ctx = await b.new_context(**opt); await harness.supabase_route(ctx)
        pg = await ctx.new_page(); js = []
        pg.on('pageerror', lambda e: js.append(str(e)))
        pg.on('console', lambda m: js.append(m.text) if m.type == 'error' and 'status of 403' not in m.text and 'favicon' not in m.text else None)
        await pg.goto(harness.URL + harness.LOGIN_HASH); await pg.wait_for_timeout(2200)
        if sp == 'en':
            await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(400)
        z = await pg.evaluate(ZUSTAND)
        t = f'{tag} {"Abo" if abo else "frei"}'
        if abo:
            pruefe(z['member'] and not z['sperre'] and z['avatar'] and not z['anmelden'] and not z['zeile'] and z['wert'] != str(z['pub']), f'{t}: aktueller Wert, keine Schranke {z}')
        else:
            text = 'Mit Premium siehst du alles live. Premium ansehen' if sp == 'de' else 'See everything live with Premium. See Premium'
            pruefe(z['member'] and z['sperre'] and (z['avatar'] or w >= 760) and not z['anmelden'], f'{t}: angemeldet mit Avatar, kein "Anmelden" {z}')
            pruefe(z['zeile'] and text in z['zeileText'] and z['wert'] == str(z['pub']), f'{t}: Hinweiszeile mit Premium-Knopf, zeitversetzter Wert {z["zeileText"]!r} {z["wert"]}/{z["pub"]}')
            if SHOT and engine == 'chromium' and sp == 'de': await pg.screenshot(path=str(SHOT / f'schranke_start_{w}.png'))
            await pg.click('.zeitversatz-premium'); await pg.wait_for_timeout(700)
            z2 = await pg.evaluate(ZUSTAND)
            pruefe(z2['paywall'], f'{t}: "Premium ansehen" oeffnet die Abo-Ansicht')
            if SHOT and engine == 'chromium' and sp == 'de': await pg.screenshot(path=str(SHOT / f'schranke_paywall_{w}.png'))
            await schliessen(pg)
            await pg.click('#alarm-karte [data-alarm]'); await pg.wait_for_timeout(700)
            pruefe((await pg.evaluate(ZUSTAND))['paywall'], f'{t}: "Alarm setzen" fuehrt zur Abo-Ansicht')
            await schliessen(pg)
            await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(700)
            await pg.fill('#ki-eingabe', 'Eine Frage'); await pg.press('#ki-eingabe', 'Enter'); await pg.wait_for_timeout(1500)
            fm = await pg.evaluate("[...document.querySelectorAll('.ki-fehler')].pop()?.innerText||''")
            pruefe(('Premium' in fm) and await pg.locator('[data-ki=premium]').count() == 1, f'{t}: KI-Frage -> Premium-Hinweis {fm!r}')
            await pg.click('[data-ki=premium]'); await pg.wait_for_timeout(700)
            pruefe((await pg.evaluate(ZUSTAND))['paywall'], f'{t}: KI-Knopf oeffnet die Abo-Ansicht')
            await schliessen(pg)
            await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1200)
            pruefe(await pg.locator('#verlauf-premium').count() == 1, f'{t}: Verlauf mit Premium-Knopf')
            z3 = await pg.evaluate(ZUSTAND)
            pruefe(z3['member'] and not z3['anmelden'], f'{t}: nach allen Wegen weiter angemeldet')
            await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(800)
            pruefe(await pg.evaluate("InvestTimer.aktiveAnsicht()==='konto'&&!!document.querySelector('#konto-ansicht-titel')"), f'{t}: Konto erreichbar')
        pruefe(not js, f'{t}: keine Konsolenfehler {js[:3]}')
        await ctx.close()
    await b.close()

async def main():
    srv, url = harness.starten(); harness.URL = url
    async with async_playwright() as p:
        for engine, geraet, w, sp in (('chromium', None, 390, 'de'), ('chromium', None, 1280, 'de'), ('chromium', None, 390, 'en'), ('webkit', 'iPhone 13', 390, 'de')):
            await lauf(p, engine, geraet, w, sp)
    harness.ZUSTAND['pflicht'] = False
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
