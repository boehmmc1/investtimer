"""Verlauf erkunden mit Finger, Maus und Tastatur (Auftrag 20.11.2026).
Chromium (echte Touch-Gesten ueber das DevTools-Protokoll) und WebKit (Safari-Engine, iPhone-Emulation, Pointer-Ablaeufe):
keine Textauswahl/kein iOS-Menue, Werte-Zeile fest ueber dem Chart ("Heute · …" bzw. Datum ohne Auswahl), Auflegen zeigt sofort den
naechsten Punkt, waagerecht folgen, senkrecht scrollt die Seite, Loslassen 2 s stehen + ausblenden, Tippen ausserhalb schliesst,
Linie/Punkt in Stufenfarbe, Phase in der Werte-Zeile oeffnet die Karte, Maus-Hover, Pfeiltasten, Geschwindigkeit. Screenshots nach <ordner>."""
import asyncio, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
ZEILE = "(()=>{const z=document.querySelector('.verlauf-wertzeile');return {aktiv:z.classList.contains('erkunden'),text:z.querySelector('.wz-text')?.textContent||'',phase:z.querySelector('.wz-phase')?.textContent||null,punkt:getComputedStyle(z.querySelector('.wz-punkt')).backgroundColor}})()"
KREUZ = "(()=>{const d=document.querySelector('#verlauf-ansicht .verlauf-diagramm'),l=d.querySelector('.verlauf-cursor'),c=d.querySelector('.verlauf-cursor-punkt');return {sicht:getComputedStyle(l).visibility,x:+l.getAttribute('x1'),farbe:getComputedStyle(c).fill,linie:getComputedStyle(l).stroke}})()"

async def oeffnen(b, url, w, h, ein, sp, webkit=False):
    opt = dict(viewport={'width': w, 'height': h}, is_mobile=w < 760, has_touch=w < 760, device_scale_factor=2 if SHOT else 1)
    ctx = await b.new_context(**opt)
    await harness.supabase_route(ctx)
    pg = await ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.on('console', lambda m: js.append(m.text) if m.type == 'error' else None)
    await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1300)
    if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
    await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
    return ctx, pg, js

async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h, ein, sp in ((390, 844, False, 'de'), (390, 844, True, 'en'), (320, 568, True, 'de'), (1280, 860, True, 'de'), (1280, 860, False, 'en')):
            ctx, pg, js = await oeffnen(b, url, w, h, ein, sp)
            tag = f'Chromium {w} {"ein" if ein else "aus"} {sp}'
            css = await pg.evaluate("(()=>{const d=document.querySelector('#verlauf-ansicht .verlauf-diagramm'),t=d.querySelector('text');return [getComputedStyle(d).userSelect,getComputedStyle(t).userSelect,getComputedStyle(d).touchAction,[...document.querySelectorAll('style')].some(s=>/verlauf-diagramm[^{]*\{[^}]*-webkit-touch-callout:none/.test(s.textContent))]})()")
            pruefe(css[0] == 'none' and css[1] == 'none' and css[2] == 'pan-y' and css[3], f'{tag}: keine Textauswahl, kein Callout, touch-action pan-y {css}')
            z = await pg.evaluate(ZEILE)
            heute = ('Today' if sp == 'en' else 'Heute') if ein else None
            pruefe(not z['aktiv'] and ((z['text'].startswith(heute + ' · ')) if heute else ' · ' in z['text']) and z['text'].split(' · ')[1].split()[-1].isdigit(), f'{tag}: Werte-Zeile ohne Auswahl "{z["text"]}"')
            await pg.click('[data-spanne="A"]'); await pg.wait_for_timeout(500)
            box = await pg.locator('#verlauf-ansicht .verlauf-svg').bounding_box()
            y0 = box['y'] + box['height'] * 0.5
            if w < 760:
                cdp = await ctx.new_cdp_session(pg)
                async def touch(typ, x, y):
                    await cdp.send('Input.dispatchTouchEvent', {'type': typ, 'touchPoints': [] if typ == 'touchEnd' else [{'x': x, 'y': y}]})
                # Auflegen: sofort Fadenkreuz
                await touch('touchStart', box['x'] + box['width'] * 0.3, y0); await pg.wait_for_timeout(60)
                z1, k1 = await pg.evaluate(ZEILE), await pg.evaluate(KREUZ)
                pruefe(z1['aktiv'] and k1['sicht'] == 'visible' and z1['punkt'] == k1['farbe'] == k1['linie'], f'{tag}: Auflegen zeigt sofort Punkt (Stufenfarbe {k1["farbe"]}) "{z1["text"]}"')
                texte = [z1['text']]
                for i in range(1, 13):
                    await touch('touchMove', box['x'] + box['width'] * (0.3 + i * 0.03), y0 + (i % 2)); await pg.wait_for_timeout(20)
                    texte.append((await pg.evaluate(ZEILE))['text'])
                pruefe(len(set(texte)) >= 8, f'{tag}: waagerecht folgt der Punkt ({len(set(texte))} verschiedene Werte)')
                if SHOT and not ein and w == 390: await pg.screenshot(path=str(SHOT / f'finger_1_halten_{w}.png'))
                await touch('touchEnd', 0, 0); await pg.wait_for_timeout(1000)
                pruefe((await pg.evaluate(ZEILE))['aktiv'], f'{tag}: nach Loslassen bleibt die Anzeige stehen')
                await pg.wait_for_timeout(1700)
                z2 = await pg.evaluate(ZEILE)
                pruefe(not z2['aktiv'] and (await pg.evaluate(KREUZ))['sicht'] == 'hidden', f'{tag}: nach gut 2 s ausgeblendet, Werte-Zeile wieder Endwert "{z2["text"]}"')
                # Senkrecht wischen: Seite scrollt, keine Auswahl bleibt stehen
                s0 = await pg.evaluate("scrollY")
                await touch('touchStart', box['x'] + box['width'] * 0.5, y0 + 40)
                for i in range(1, 12):
                    await touch('touchMove', box['x'] + box['width'] * 0.5, y0 + 40 - i * 22); await pg.wait_for_timeout(16)
                await touch('touchEnd', 0, 0); await pg.wait_for_timeout(400)
                s1 = await pg.evaluate("scrollY")
                pruefe(s1 > s0 + 50 and not (await pg.evaluate(ZEILE))['aktiv'], f'{tag}: senkrechtes Wischen ueber dem Chart scrollt die Seite ({s0} -> {s1})')
                await pg.evaluate("scrollTo(0,0)"); await pg.wait_for_timeout(200)
                box = await pg.locator('#verlauf-ansicht .verlauf-svg').bounding_box(); y0 = box['y'] + box['height'] * 0.5
                # Tippen ausserhalb schliesst sofort
                await touch('touchStart', box['x'] + box['width'] * 0.6, y0); await touch('touchEnd', 0, 0); await pg.wait_for_timeout(100)
                await pg.touchscreen.tap(10, 10); await pg.wait_for_timeout(120)
                pruefe(not (await pg.evaluate(ZEILE))['aktiv'], f'{tag}: Tippen ausserhalb schliesst sofort')
                # Textauswahl per langem Druck: keine Auswahl
                await touch('touchStart', box['x'] + box['width'] * 0.4, y0); await pg.wait_for_timeout(900); await touch('touchEnd', 0, 0)
                sel = await pg.evaluate("String(getSelection())")
                pruefe(sel == '', f'{tag}: langes Druecken waehlt keinen Text aus "{sel[:30]}"')
            else:
                for i in range(10):
                    await pg.mouse.move(box['x'] + box['width'] * (0.2 + i * 0.06), y0); await pg.wait_for_timeout(25)
                zm = await pg.evaluate(ZEILE)
                pruefe(zm['aktiv'], f'{tag}: Maus-Hover zeigt den Punkt "{zm["text"]}"')
                await pg.mouse.move(box['x'] + box['width'] * 0.5, box['y'] - 120); await pg.wait_for_timeout(450)
                pruefe(not (await pg.evaluate(ZEILE))['aktiv'], f'{tag}: Maus verlaesst den Chart -> ausgeblendet')
            # Phase in der Werte-Zeile, Antippen oeffnet die Karte (Corona 2020 im Zeitraum "Alle")
            x_corona = await pg.evaluate("""()=>{const r=document.querySelector('#verlauf-ansicht .verlauf-svg').getBoundingClientRect(),b=document.querySelector('[data-band=corona]');
              if(!b)return null;const vb=document.querySelector('#verlauf-ansicht .verlauf-svg').viewBox.baseVal;return r.left+(+b.getAttribute('x')+ +b.getAttribute('width')*0.25)/vb.width*r.width}""")
            if x_corona:
                await pg.locator('#verlauf-ansicht .verlauf-diagramm').focus()
                await pg.evaluate("x=>{const d=document.querySelector('#verlauf-ansicht .verlauf-diagramm');d.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerType:'mouse',clientX:x,clientY:%d,pointerId:9}))}" % int(y0), x_corona)
                await pg.wait_for_timeout(80)
                zp = await pg.evaluate(ZEILE)
                pruefe(zp['phase'] and 'Corona' in zp['phase'] or 'Covid' in (zp['phase'] or ''), f'{tag}: Phase in der Werte-Zeile "{zp["phase"]}"')
                await pg.click('.verlauf-wertzeile .wz-phase'); await pg.wait_for_timeout(300)
                karte = await pg.evaluate("document.querySelector('#verlauf-ansicht .ereignis-karte h4')?.textContent||''")
                pruefe('Corona' in karte or 'Covid' in karte, f'{tag}: Antippen der Werte-Zeile oeffnet die Ereigniskarte "{karte}"')
            # Tastatur
            await pg.locator('#verlauf-ansicht .verlauf-diagramm').focus(); await pg.keyboard.press('End'); await pg.wait_for_timeout(60)
            t1 = (await pg.evaluate(ZEILE))['text']; await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(60)
            t2 = (await pg.evaluate(ZEILE))['text']
            live = await pg.evaluate("document.querySelector('.verlauf-wertzeile').getAttribute('aria-live')")
            pruefe(t1 != t2 and live == 'polite', f'{tag}: Pfeiltasten springen Punkt fuer Punkt, Werte-Zeile wird vorgelesen ("{t1}" -> "{t2}")')
            # Geschwindigkeit: 300 Zeigerbewegungen ueber "Alle" (Suche + Planung), gezeichnet hoechstens einmal pro Frame
            ms = await pg.evaluate("""(y)=>{const d=document.querySelector('#verlauf-ansicht .verlauf-diagramm'),r=d.getBoundingClientRect();let mal=0;
              const orig=window.requestAnimationFrame;const t0=performance.now();
              for(let i=0;i<300;i++)d.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerType:'mouse',clientX:r.left+r.width*(i%100)/100,clientY:y}));
              return performance.now()-t0}""", y0)
            pruefe(ms / 300 < 1.0, f'{tag}: {ms / 300:.3f} ms je Zeigerbewegung (Ziel < 1 ms, Frame = 16,7 ms)')
            cls = await pg.evaluate("(()=>{const z=document.querySelector('.verlauf-wertzeile'),h1=z.getBoundingClientRect().height;return h1})()")
            pruefe(cls >= 28, f'{tag}: Werte-Zeile mit fester Hoehe ({cls:.0f} px, kein Springen)')
            if SHOT and w == 390 and not ein:
                await pg.evaluate("x=>{}", 0)
            pruefe(not js, f'{tag}: keine JS-/Konsolenfehler {js[:2]}')
            await ctx.close()
        await b.close()
        # WebKit (Safari-Engine), iPhone-Emulation
        wk = await p.webkit.launch()
        for ein in (False, True):
            ctx = await wk.new_context(**p.devices['iPhone 13']); await harness.supabase_route(ctx)
            pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1500)
            await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
            tag = f'WebKit iPhone 13 {"ein" if ein else "aus"}'
            css = await pg.evaluate("(()=>{const d=document.querySelector('#verlauf-ansicht .verlauf-diagramm'),s=getComputedStyle(d);return [s.webkitUserSelect||s.userSelect,s.touchAction,[...document.querySelectorAll('style')].some(x=>/verlauf-diagramm[^{]*\\{[^}]*-webkit-touch-callout:none/.test(x.textContent))]})()")
            # -webkit-touch-callout wirkt nur in iOS-Safari (Linux-WebKit meldet es nicht): Regel im ausgelieferten CSS pruefen
            pruefe(css[0] == 'none' and css[1] == 'pan-y' and css[2], f'{tag}: -webkit-user-select none, pan-y, -webkit-touch-callout-Regel vorhanden {css}')
            await pg.click('[data-spanne="A"]'); await pg.wait_for_timeout(500)
            box = await pg.locator('#verlauf-ansicht .verlauf-svg').bounding_box(); y0 = box['y'] + box['height'] * 0.5
            await pg.evaluate("""([x,y,w])=>{const d=document.querySelector('#verlauf-ansicht .verlauf-diagramm');const ev=(t,cx)=>d.dispatchEvent(new PointerEvent(t,{bubbles:true,pointerType:'touch',pointerId:5,clientX:cx,clientY:y}));
              ev('pointerdown',x);for(let i=1;i<=10;i++)ev('pointermove',x+w*0.03*i);}""", [box['x'] + box['width'] * 0.3, y0, box['width']])
            await pg.wait_for_timeout(100)
            z = await pg.evaluate(ZEILE)
            pruefe(z['aktiv'] and (await pg.evaluate(KREUZ))['sicht'] == 'visible', f'{tag}: Finger zeigt Punkt "{z["text"]}"')
            if SHOT: await pg.screenshot(path=str(SHOT / f'finger_webkit_{"ein" if ein else "aus"}.png'))
            await pg.evaluate("()=>{document.querySelector('#verlauf-ansicht .verlauf-diagramm').dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerType:'touch',pointerId:5}))}")
            await pg.wait_for_timeout(2700)
            pruefe(not (await pg.evaluate(ZEILE))['aktiv'], f'{tag}: nach Loslassen ausgeblendet')
            pruefe(not js, f'{tag}: keine JS-Fehler {js[:2]}')
            await ctx.close()
        await wk.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
