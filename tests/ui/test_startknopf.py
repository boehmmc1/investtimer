"""Nachtrag L (27.11.2026): Logo "InvestTimer" oben links als Startseiten-Knopf. Echter Link (href "/"), aria-label "Zur Startseite"/"Home",
Klickflaeche >= 44 px, kein Unterstrich. Aus jedem Reiter (Aufbau, Verlauf, KI) und aus dem Konto: Ansicht Marktstress, ganz oben, Reiter
"Marktstress" aktiv, ohne Neuladen; Zurueck fuehrt in die vorige Ansicht. Offene Blaetter/Dialoge/Menues zu; Alarm-Blatt mit ungespeicherter
Aenderung: Rueckfrage "Aenderungen verwerfen?". Gescrollt: nach oben. Oben: Wert neu laden (stress.json, no-store) mit Lade-Hinweis an der Pille
bzw. ausgeloggt an der Hinweiszeile, danach "Aktualisiert"; Sperre 10 s. KI-Unterhaltung bleibt erhalten. Keine Konsolenfehler.
Geraete: Android Chrome (Pixel 7), iPhone Safari (WebKit iPhone 13), installierte Web-App (iPhone, standalone), Desktop 1280; ein- und ausgeloggt."""
import asyncio, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)

STANDALONE = """(()=>{const mm=window.matchMedia.bind(window);window.matchMedia=q=>/display-mode:\\s*standalone/.test(q)?
 {matches:true,media:q,onchange:null,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){},dispatchEvent(){return false}}:mm(q);
 try{Object.defineProperty(Navigator.prototype,'standalone',{configurable:true,get:()=>true})}catch(e){}})()"""
ZUSTAND = """()=>({hash:location.hash,ansicht:InvestTimer.aktiveAnsicht&&InvestTimer.aktiveAnsicht(),y:Math.round(scrollY),marke:window.__startMarke===1,
 aktiv:[...document.querySelectorAll('.it-leiste a[aria-current=page],.it-tabs a[aria-current=page]')].filter(a=>a.offsetParent).map(a=>a.dataset.ziel),
 dialoge:[...document.querySelectorAll('dialog[open]')].map(d=>d.className||d.id)})"""

async def logo_tippen(pg):
    """Tippen auf die Stelle des Logos (wie ein Finger: trifft bei offenem modalem Blatt den Hintergrund des Blatts)"""
    r = await pg.evaluate("(()=>{const r=document.querySelector('a.wordmark').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()")
    await pg.mouse.click(r[0], r[1]); await pg.wait_for_timeout(700)

async def zum_reiter(pg, ziel):
    await pg.evaluate("z=>{const a=[...document.querySelectorAll('.it-leiste a[data-ziel],.it-tabs a[data-ziel]')].find(a=>a.offsetParent&&a.dataset.ziel===z);a.click()}", ziel)
    await pg.wait_for_timeout(500)

async def lauf(p, name, engine, geraet, w, ein, installiert=False):
    b = await (p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']) if engine == 'chromium' else p.webkit.launch())
    opt = dict(p.devices[geraet]) if geraet else dict(viewport={'width': w, 'height': 860})
    if engine == 'chromium': opt.pop('default_browser_type', None)
    ctx = await b.new_context(**opt); await harness.supabase_route(ctx)
    if installiert: await ctx.add_init_script(STANDALONE)
    pg = await ctx.new_page(); js = []; abrufe = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.on('console', lambda m: js.append(m.text) if m.type == 'error' and 'favicon' not in m.text and not (engine == 'webkit' and '403' in m.text) else None)
    pg.on('response', lambda r: js.append(f'{r.status} {r.url}') if r.status >= 400 and 'favicon' not in r.url and 'supabase.co' not in r.url else None)  # WebKit: abgefangene Supabase-Aufrufe ohne CORS-Kopf = 403 (Test-Attrappe)
    pg.on('request', lambda r: abrufe.append(r.url) if '/data/stress.json' in r.url else None)
    tag = f'{name} {"ein" if ein else "aus"}'
    await pg.goto(harness.URL + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1900)
    await pg.evaluate("window.__startMarke=1")

    # 1. Link, Beschriftung, Groesse
    l = await pg.evaluate("""()=>{const a=document.querySelector('a.wordmark');if(!a)return null;const r=a.getBoundingClientRect(),cs=getComputedStyle(a);
      return {href:a.getAttribute('href'),aria:a.getAttribute('aria-label'),h:Math.round(r.height),w:Math.round(r.width),deko:cs.textDecorationLine}}""")
    pruefe(l and l['href'] == '/' and l['aria'] == 'Zur Startseite' and l['h'] >= 44 and l['w'] >= 44 and l['deko'] == 'none', f'{tag}: Logo ist Link "/" {l}')
    await pg.focus('a.wordmark')
    fokus = await pg.evaluate("getComputedStyle(document.activeElement).outlineStyle")
    await pg.keyboard.press('Tab'); await pg.keyboard.press('Shift+Tab')
    fokus2 = await pg.evaluate("document.activeElement.matches('a.wordmark')&&getComputedStyle(document.activeElement).outlineStyle")
    pruefe(fokus2 not in (None, False, 'none'), f'{tag}: sichtbarer Fokus ({fokus}/{fokus2})')
    await pg.evaluate("document.activeElement.blur()")

    # 2. aus jedem Reiter
    reiter = ['aufbau', 'verlauf', 'ki']
    for r in reiter:
        await zum_reiter(pg, r)
        await pg.evaluate("(()=>{const r=document.querySelector('a.wordmark').getBoundingClientRect();scrollTo(0,Math.max(3,Math.floor(scrollY+r.top)-1))})()"); await pg.wait_for_timeout(150)  # Kopfzeile scrollt mit: so weit, wie das Logo noch sichtbar ist
        await logo_tippen(pg)
        z = await pg.evaluate(ZUSTAND)
        pruefe(z['ansicht'] == 'stress' and z['hash'] == '' and z['y'] == 0 and z['marke'] and z['aktiv'] and set(z['aktiv']) == {'stress'},
               f'{tag}: aus {r} zur Startseite, oben, Reiter aktiv, ohne Neuladen {z}')
        await pg.go_back(); await pg.wait_for_timeout(600)
        z = await pg.evaluate(ZUSTAND)
        pruefe(z['ansicht'] == r and z['marke'], f'{tag}: Zurueck fuehrt wieder nach {r} {z["ansicht"]}')
        await pg.go_forward(); await pg.wait_for_timeout(500)

    # 3. aus dem Konto (eingeloggt) bzw. mit offenem Anmeldedialog (ausgeloggt)
    if ein:
        await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(600)
        await logo_tippen(pg); z = await pg.evaluate(ZUSTAND)
        pruefe(z['ansicht'] == 'stress' and z['y'] == 0 and z['marke'], f'{tag}: aus dem Konto zur Startseite {z}')
    else:
        await pg.click('#account-login'); await pg.wait_for_timeout(600)
        offen = await pg.evaluate("document.querySelectorAll('dialog[open]').length")
        await logo_tippen(pg); z = await pg.evaluate(ZUSTAND)
        pruefe(offen and not z['dialoge'] and z['ansicht'] == 'stress', f'{tag}: Anmeldedialog offen -> geschlossen {z["dialoge"]}')

    # 4. Aufbau-Reiter mit offenem Erklaerblatt
    await zum_reiter(pg, 'aufbau')
    await pg.evaluate("document.querySelector('[data-erkl]').click()"); await pg.wait_for_timeout(500)
    offen = await pg.evaluate("!!document.querySelector('dialog.aufbau-blatt[open]')")
    await logo_tippen(pg); z = await pg.evaluate(ZUSTAND)
    pruefe(offen and not z['dialoge'] and z['ansicht'] == 'stress' and z['y'] == 0, f'{tag}: Erklaerblatt offen -> zu, Startseite {z}')

    # 5. Alarm-Blatt (eingeloggt): ohne Aenderung direkt zu, mit Aenderung Rueckfrage
    if ein:
        await pg.evaluate("InvestTimer.alarmNeu&&InvestTimer.alarmNeu()"); await pg.wait_for_timeout(600)
        if SHOT and name == 'iphone': await pg.screenshot(path=str(SHOT / 'startknopf_blatt.png'))
        await logo_tippen(pg); z = await pg.evaluate(ZUSTAND)
        pruefe(not z['dialoge'], f'{tag}: Alarm-Blatt ohne Aenderung -> zu {z["dialoge"]}')
        await zum_reiter(pg, 'verlauf'); await pg.evaluate("InvestTimer.alarmNeu&&InvestTimer.alarmNeu()"); await pg.wait_for_timeout(600)
        await pg.click('.alarm-blatt [data-schritt="1"]'); await pg.wait_for_timeout(250)
        await logo_tippen(pg)
        f = await pg.evaluate("(()=>{const d=document.querySelector('dialog.start-frage[open]');return d?d.innerText:null})()")
        pruefe(f and 'Änderungen verwerfen?' in f, f'{tag}: Rueckfrage bei ungespeichertem Alarm {f!r}')
        if SHOT and name == 'iphone': await pg.screenshot(path=str(SHOT / 'startknopf_rueckfrage.png'))
        await pg.click('.start-frage [data-start=bleiben]'); await pg.wait_for_timeout(400)
        z = await pg.evaluate(ZUSTAND)
        pruefe(z['dialoge'] == ['alarm-blatt'] and z['ansicht'] == 'verlauf', f'{tag}: "Weiter bearbeiten" laesst Blatt offen {z}')
        await logo_tippen(pg)
        await pg.click('.start-frage [data-start=verwerfen]'); await pg.wait_for_timeout(700)
        z = await pg.evaluate(ZUSTAND)
        pruefe(not z['dialoge'] and z['ansicht'] == 'stress', f'{tag}: "Verwerfen" schliesst und wechselt {z}')
        # Konto-Menue (Desktop)
        if w >= 760 and await pg.locator('#konto-menue').count():
            await pg.evaluate("document.querySelector('[aria-controls=konto-menue]').click()"); await pg.wait_for_timeout(300)
            auf = await pg.evaluate("!document.querySelector('#konto-menue').hidden")
            await logo_tippen(pg)
            zu = await pg.evaluate("document.querySelector('#konto-menue').hidden")
            pruefe(auf and zu, f'{tag}: Konto-Menue zu ({auf}/{zu})')

    # 6. KI-Unterhaltung (eingeloggt) bzw. angefangene Frage (ausgeloggt) bleibt
    await zum_reiter(pg, 'ki')
    if ein:
        await pg.evaluate("document.querySelector('#ki-ansicht .ki-frage').click()"); await pg.wait_for_timeout(300)
        await pg.evaluate("document.querySelector('#ki-ansicht form').requestSubmit()"); await pg.wait_for_timeout(2500)
    else:
        await pg.evaluate("(()=>{const i=document.querySelector('#ki-eingabe');if(i){i.value='Testfrage';i.dispatchEvent(new Event('input',{bubbles:true}))}})()")
    vor = await pg.evaluate("[document.querySelector('#ki-ansicht').classList.contains('ki-ist-gespraech'),(document.querySelector('#ki-ansicht .ki-innen')||{innerText:''}).innerText.length,(document.querySelector('#ki-eingabe')||{}).value||'']")
    await pg.evaluate("scrollTo(0,0)"); await logo_tippen(pg); await zum_reiter(pg, 'ki'); await pg.wait_for_timeout(300)
    nach = await pg.evaluate("[document.querySelector('#ki-ansicht').classList.contains('ki-ist-gespraech'),(document.querySelector('#ki-ansicht .ki-innen')||{innerText:''}).innerText.length,(document.querySelector('#ki-eingabe')||{}).value||'']")
    pruefe((vor[0] and nach[0] and nach[1] == vor[1]) if ein else (nach[2] == vor[2]), f'{tag}: KI-Unterhaltung/Eingabe bleibt erhalten {vor[:2]} {nach[:2]}')
    await pg.evaluate("scrollTo(0,0)"); await logo_tippen(pg)

    # 7. gescrollt: nach oben
    await pg.evaluate("(()=>{const r=document.querySelector('a.wordmark').getBoundingClientRect();scrollTo(0,Math.max(3,Math.floor(scrollY+r.top)-1))})()"); await pg.wait_for_timeout(300)
    n0 = len(abrufe)
    await logo_tippen(pg); await pg.wait_for_timeout(600)
    z = await pg.evaluate(ZUSTAND)
    pruefe(z['y'] == 0 and len(abrufe) == n0, f'{tag}: gescrollt -> nach oben, kein Neuladen {z["y"]}')

    # 8. oben: Neuladen mit Hinweis, Sperre 10 s (vorher 10 s Abstand zu einem frueheren Logo-Tippen oben)
    await pg.wait_for_timeout(10500)
    await pg.evaluate("""()=>{window.__startKlassen=[];new MutationObserver(m=>m.forEach(x=>{const c=x.target.className;if(typeof c==='string'&&/start-(laedt|frisch)/.test(c))window.__startKlassen.push((x.target.id||x.target.className.split(' ')[0])+':'+c.match(/start-(laedt|frisch)/)[0])}))
      .observe(document.body,{attributes:true,attributeFilter:['class'],subtree:true})}""")
    n0 = len(abrufe)
    await logo_tippen(pg); await pg.wait_for_timeout(200)
    if SHOT and name in ('iphone', 'desktop'): await pg.screenshot(path=str(SHOT / f'startknopf_laedt_{name}_{"ein" if ein else "aus"}.png'), clip={'x': 0, 'y': 0, 'width': w, 'height': 260})
    await pg.wait_for_timeout(700)
    if SHOT and name in ('iphone', 'desktop'): await pg.screenshot(path=str(SHOT / f'startknopf_aktualisiert_{name}_{"ein" if ein else "aus"}.png'), clip={'x': 0, 'y': 0, 'width': w, 'height': 260})
    kl = await pg.evaluate("window.__startKlassen")
    ziel = 'snapshot-label' if ein else 'zeitversatz-zeile'
    pruefe(len(abrufe) == n0 + 1, f'{tag}: oben -> Wert neu geladen ({len(abrufe) - n0} Abruf)')
    pruefe(any(k.startswith(ziel) and k.endswith('laedt') for k in kl) and any(k.startswith(ziel) and k.endswith('frisch') for k in kl), f'{tag}: Lade-Hinweis und "Aktualisiert" an {ziel} {kl[:4]}')
    ansage = await pg.evaluate("document.querySelector('.start-ansage').textContent")
    pruefe(ansage == 'Aktualisiert', f'{tag}: Ansage "Aktualisiert" ({ansage!r})')
    n1 = len(abrufe)
    await logo_tippen(pg); await pg.wait_for_timeout(500)
    pruefe(len(abrufe) == n1, f'{tag}: zweites Tippen innerhalb 10 s laedt nicht ({len(abrufe) - n1})')
    await pg.wait_for_timeout(9500)
    await logo_tippen(pg); await pg.wait_for_timeout(500)
    pruefe(len(abrufe) == n1 + 1, f'{tag}: nach 10 s wieder Neuladen ({len(abrufe) - n1})')
    z = await pg.evaluate(ZUSTAND)
    pruefe(z['marke'], f'{tag}: Seite wurde nie neu geladen')

    # 9. Englisch
    await pg.evaluate("()=>{const h=document.querySelector('#header-language');if(h){h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}}"); await pg.wait_for_timeout(300)
    pruefe(await pg.evaluate("document.querySelector('a.wordmark').getAttribute('aria-label')") == 'Home', f'{tag}: EN aria-label "Home"')
    pruefe(not js, f'{tag}: keine Konsolenfehler {js[:3]}')
    await ctx.close(); await b.close()

async def main():
    srv, url = harness.starten(); harness.URL = url
    async with async_playwright() as p:
        for name, engine, geraet, w, inst in (('android', 'chromium', 'Pixel 7', 412, False), ('iphone', 'webkit', 'iPhone 13', 390, False),
                                              ('iphone-app', 'webkit', 'iPhone 13', 390, True), ('desktop', 'chromium', None, 1280, False)):
            if os.environ.get('IT_NUR') and os.environ['IT_NUR'] != name: continue
            for ein in (False, True):
                await lauf(p, name, engine, geraet, w, ein, inst)
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
