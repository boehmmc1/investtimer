"""Block J (Auftrag 25.11.2026): KI-Tab unten aufgeraeumt. Kugel in Originalgroesse, erste Fragen-Karte mit allen 3 Fragen ohne Scrollen
ganz sichtbar (375x812, 390x844), Unterkante >= 12 px ueber dem weichen Uebergang, alle Karten gleich hoch, keine harte Linie, Hinweise auf
einer Zeile mit Info-Symbol (44 px) und Info-Feld, Text nach Verbrauch, Tastatur offen, Desktop max. 680 px. Screenshots nach <ordner>."""
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

async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for ein in (True, False):
            for w, h in ((375, 812), (390, 844), (430, 932), (375, 667), (1280, 860)):
                tag = f'{w}x{h} {"ein" if ein else "aus"}'
                mobil = w < 760
                harness.ZUSTAND['frei'] = {'verbraucht': False, 'ausgelastet': False}
                ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=mobil, has_touch=mobil, device_scale_factor=2 if SHOT else 1)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1500)
                await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(1400)
                m = await pg.evaluate("""()=>{const u=document.querySelector('.ki-unten'),k=[...document.querySelectorAll('.ki-gruppe')],ku=document.querySelector('.ki-kugel,canvas.ki-kugel,.ki-ansicht canvas');
                  const ur=u.getBoundingClientRect(),erste=k[0].getBoundingClientRect(),cs=getComputedStyle(u),vor=getComputedStyle(u,'::before');
                  return {unten:Math.round(ur.top),ersteUnten:Math.round(erste.bottom),ersteRechts:Math.round(erste.right),fragen:k[0].querySelectorAll('.ki-frage').length,
                   hoehen:[...new Set(k.map(x=>Math.round(x.getBoundingClientRect().height)))],linie:cs.borderTopWidth,uebergang:vor.content!=='none'?parseFloat(vor.height):0,
                   kugel:ku?Math.round(ku.getBoundingClientRect().width):0,scroll:Math.round(scrollY),zeile:u.querySelector('.ki-hinweiszeile')?.innerText.trim()||'',
                   info:u.querySelector('.ki-info')?[Math.round(u.querySelector('.ki-info').getBoundingClientRect().width),u.querySelector('.ki-info').getAttribute('aria-label')]:null,
                   breite:Math.round((document.querySelector('.ki-gruppen')||document.body).getBoundingClientRect().width)}}""")
                if mobil:
                    luft = m['unten'] - m['uebergang'] - m['ersteUnten']
                    if h >= 760:
                        pruefe(m['fragen'] == 3 and luft >= 12 and m['scroll'] == 0, f'{tag}: erste Karte ganz sichtbar, {luft} px ueber dem Uebergang')
                    pruefe(m['linie'] == '0px' and m['uebergang'] == 32, f'{tag}: keine harte Linie, Uebergang 32 px ({m["linie"]}, {m["uebergang"]})')
                    pruefe(len(m['hoehen']) == 1, f'{tag}: alle Karten gleich hoch {m["hoehen"]}')
                else:
                    pruefe(m['breite'] <= 680, f'{tag}: Desktop max. 680 px ({m["breite"]})')
                pruefe(m['kugel'] >= (104 if h < 760 else 120), f'{tag}: Kugel {m["kugel"]} px')
                erwartet = '1 freie Frage heute · KI, keine Anlageberatung' if ein else 'KI, keine Anlageberatung'
                pruefe(m['zeile'] == erwartet and m['info'] and m['info'][0] >= 44 and m['info'][1] == 'Mehr zur KI', f'{tag}: Hinweiszeile "{m["zeile"]}" {m["info"]}')
                await pg.click('.ki-info'); await pg.wait_for_timeout(250)
                f = await pg.evaluate("(()=>{const f=document.querySelector('.ki-info-feld');return f&&!f.hidden?f.innerText:''})()")
                pruefe('So funktioniert die KI' in f and 'Eine eigene Frage pro Tag ist frei' in f and 'Keine Anlageberatung' in f, f'{tag}: Info-Feld')
                if SHOT and w in (390, 1280): await pg.screenshot(path=str(SHOT / f'ki_info_{"ein" if ein else "aus"}_{w}.png'))
                await pg.click('.ki-info'); await pg.wait_for_timeout(200)
                if SHOT and w in (390, 1280): await pg.screenshot(path=str(SHOT / f'ki_{"ein" if ein else "aus"}_{w}.png'))
                if ein and mobil and h >= 800:
                    await pg.set_viewport_size({'width': w, 'height': h // 2 + 40}); await pg.focus('#ki-eingabe'); await pg.wait_for_timeout(500)
                    t = await pg.evaluate("(()=>{const r=document.querySelector('#ki-eingabe').getBoundingClientRect();return [Math.round(r.bottom),innerHeight]})()")
                    pruefe(t[0] <= t[1], f'{tag}: Tastatur offen, Eingabe sichtbar {t}')
                    await pg.set_viewport_size({'width': w, 'height': h})
                pruefe(not js, f'{tag}: keine JS-Fehler {js[:2]}')
                await ctx.close()
        # Tagesfrage verbraucht
        harness.ZUSTAND['frei'] = {'verbraucht': True, 'ausgelastet': False}
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        await harness.supabase_route(ctx); pg = await ctx.new_page()
        await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1500)
        await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(1500)
        z = await pg.evaluate("[document.querySelector('.ki-hinweiszeile').innerText.trim(),document.querySelector('#ki-eingabe').disabled]")
        pruefe(z == ['Heutige freie Frage genutzt · KI, keine Anlageberatung', True], f'verbraucht: {z}')
        if SHOT: await pg.screenshot(path=str(SHOT / 'ki_verbraucht_390.png'))
        await ctx.close()
        harness.ZUSTAND['frei'] = {'verbraucht': False, 'ausgelastet': False}
        await b.close()
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
