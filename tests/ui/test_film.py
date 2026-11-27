"""Block G (Auftrag 25.11.2026): Film-Karte nur ausgeloggt, direkt unter der Aufbau-Karte; Video wird erst beim Tippen geladen,
spielt inline mit Steuerelementen, ohne Ton; Abspielknopf 56 px mit aria-label; eingeloggt keine Karte; reduzierte Bewegung: nur Standbild
bis zum Tippen; WebKit (iPhone 13) spielt inline. Laeuft nur, wenn die Seite mit IT_FILM=1 gebaut ist. Screenshots nach <ordner>."""
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
    if not (harness.PUBLIC / 'media' / 'film-marktstress.mp4').exists():
        print('ok   Film aus (IT_FILM=0): keine Pruefung'); print('FEHLER: 0'); return
    srv, url = harness.starten()
    async with async_playwright() as p:
        for engine, geraet in (('chromium', None), ('webkit', 'iPhone 13')):
            b = await (p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']) if engine == 'chromium' else p.webkit.launch())
            for w, h, ein, ruhig in (((390, 844, False, False), (1280, 860, False, False), (390, 844, True, False), (390, 844, False, True)) if engine == 'chromium' else ((390, 844, False, False),)):
                tag = f'{engine} {w} {"ein" if ein else "aus"}{" reduziert" if ruhig else ""}'
                opt = dict(p.devices[geraet]) if geraet else dict(viewport={'width': w, 'height': h}, is_mobile=w < 760, has_touch=w < 760)
                if ruhig: opt['reduced_motion'] = 'reduce'
                ctx = await b.new_context(**opt); await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []; videos = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                pg.on('request', lambda r: videos.append(r.url) if 'film-marktstress.mp4' in r.url else None)
                await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1800)
                k = await pg.evaluate("""()=>{const k=document.querySelector('#film-karte');if(!k)return null;const b=k.querySelector('.film-play').getBoundingClientRect();
                  return {nachAufbau:k.previousElementSibling&&k.previousElementSibling.id==='aufbau-karte',vorAlarm:k.nextElementSibling&&k.nextElementSibling.id==='alarm-karte',
                   knopf:[Math.round(b.width),Math.round(b.height)],aria:k.querySelector('.film-play').getAttribute('aria-label'),label:k.querySelector('.film-label').textContent,
                   titel:k.querySelector('h3').textContent,video:!!k.querySelector('video')}}""")
                if ein:
                    pruefe(k is None, f'{tag}: eingeloggt keine Film-Karte')
                else:
                    pruefe(k and k['nachAufbau'] and k['vorAlarm'] and k['knopf'] == [56, 56] and k['aria'] == 'Film abspielen: So liest du den Marktstress'
                           and k['label'] == 'KURZ ERKLÄRT' and k['titel'] == 'So liest du den Marktstress' and not k['video'], f'{tag}: Karte unter der Aufbau-Karte {k}')
                    pruefe(not videos, f'{tag}: Video vor dem Tippen nicht geladen')
                    await pg.locator('#film-karte').scroll_into_view_if_needed()
                    if SHOT and engine == 'chromium' and not ruhig: await pg.screenshot(path=str(SHOT / f'film_karte_{w}.png'))
                    await pg.click('.film-play'); await pg.wait_for_timeout(1500)
                    v = await pg.evaluate("""()=>{const v=document.querySelector('#film-karte video');return v?{inline:v.hasAttribute('playsinline'),controls:v.controls,
                      zeit:v.currentTime,pausiert:v.paused,voll:!!document.fullscreenElement,ton:v.mozHasAudio??(v.audioTracks?v.audioTracks.length:null)}:null}""")
                    pruefe(v and v['inline'] and v['controls'] and not v['voll'] and videos, f'{tag}: spielt inline mit Steuerelementen {v}')
                pruefe(not js, f'{tag}: keine JS-Fehler {js[:2]}')
                await ctx.close()
            await b.close()
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
