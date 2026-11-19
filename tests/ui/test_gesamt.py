"""Gesamtpruefung (Auftrag Block 9): alle Ansichten, ausgeloggt/eingeloggt, DE/EN, 320 bis 1440 px plus Querformat und offene Tastatur.
Je Ansicht: Sicht/Ueberdeckung (oben und ganz unten gescrollt), horizontales Scrollen, Klickflaechen, Kontrast, Einzelworte in
Ueberschriften, Begriffe, Konsolenfehler. Ausgabe: Befundliste (JSON) und Zusammenfassung.
Aufruf: test_gesamt.py <befunde.json> [--schnell]"""
import asyncio, json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
PRUEF = (Path(__file__).parent / 'pruefen.js').read_text()
GESAMT = (Path(__file__).parent / 'gesamtpruefung.js').read_text()
SCHNELL = '--schnell' in sys.argv
GROESSEN = [(320, 568), (375, 667), (390, 844), (430, 932), (768, 1024), (1024, 768), (1280, 860), (1440, 900), (844, 390)]
if SCHNELL: GROESSEN = [(320, 568), (390, 844), (1280, 860)]
befunde = []

async def ansicht_pruefen(pg, name, meta, erlaubt=(), datenstand=2):
    js_vorher = len(meta['js'])
    await pg.evaluate("window.scrollTo({top:0,behavior:'instant'})"); await pg.wait_for_timeout(250)
    a = await pg.evaluate(PRUEF, {'bereich': 'oben'})
    g = await pg.evaluate(GESAMT, {'erlaubt': list(erlaubt), 'datenstandMax': datenstand})
    hoch = await pg.evaluate("document.querySelector('dialog[open]')?0:document.documentElement.scrollHeight-innerHeight")
    b = []
    if hoch > 40:
        await pg.evaluate("window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})"); await pg.wait_for_timeout(350)
        b = await pg.evaluate(PRUEF, {'bereich': 'unten'})
    for f in dict.fromkeys(a + b + g):
        befunde.append(dict(meta['kontext'], ansicht=name, befund=f))
    for e in meta['js'][js_vorher:]:
        befunde.append(dict(meta['kontext'], ansicht=name, befund='JS-Fehler: ' + e[:120]))

async def lauf(br, url, w, h, ein, sprache):
    ctx = await br.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=1)
    await harness.supabase_route(ctx)
    pg = await ctx.new_page()
    meta = {'js': [], 'kontext': {'groesse': f'{w}x{h}', 'zustand': 'ein' if ein else 'aus', 'sprache': sprache}}
    pg.on('pageerror', lambda e: meta['js'].append(str(e)))
    pg.on('console', lambda m: meta['js'].append('console: ' + m.text) if m.type == 'error' and 'favicon' not in m.text else None)
    await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1300)
    if sprache == 'en':
        await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(400)
    mobil = w < 760
    await ansicht_pruefen(pg, 'Startseite', meta)
    await pg.click('#details-toggle'); await pg.wait_for_timeout(500)
    await pg.click('[data-perspective="volatility"] summary'); await pg.wait_for_timeout(200)
    await ansicht_pruefen(pg, 'Mehr erfahren', meta)
    await pg.click('[data-explain]'); await pg.wait_for_timeout(400)
    await ansicht_pruefen(pg, 'Erklaerdialog', meta)
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
    await pg.evaluate("window.scrollTo(0,0)")
    await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(900)
    await ansicht_pruefen(pg, 'KI Start', meta)
    if ein:
        await pg.click('.ki-gruppe:not(.ki-gruppe-halb) .ki-frage'); await pg.press('#ki-eingabe', 'Enter')
        await pg.wait_for_selector('.ki-antwort', timeout=8000); await pg.wait_for_timeout(900)
        await ansicht_pruefen(pg, 'KI Gespraech', meta)
        if mobil:  # offene Tastatur: sichtbarer Bereich ~ halbe Hoehe
            await pg.set_viewport_size({'width': w, 'height': max(300, h // 2 + 40)}); await pg.focus('#ki-eingabe'); await pg.wait_for_timeout(500)
            await ansicht_pruefen(pg, 'KI Gespraech, Tastatur offen', meta)
            await pg.set_viewport_size({'width': w, 'height': h}); await pg.wait_for_timeout(300)
        await pg.click('[data-ki=neu]'); await pg.wait_for_timeout(300)
    await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1300)
    for sp in ('1M', '1J', 'A'):
        await pg.click('[data-spanne="%s"]' % sp); await pg.wait_for_timeout(400)
        await ansicht_pruefen(pg, 'Verlauf ' + sp, meta, erlaubt=())
    await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(900)
    await ansicht_pruefen(pg, 'Konto', meta)
    if ein:
        await pg.click('.konto-alarm'); await pg.wait_for_timeout(700)
        await ansicht_pruefen(pg, 'Alarme (Dialog)', meta)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        if not mobil:
            await pg.evaluate("window.scrollTo(0,0)"); await pg.click('#konto-knopf'); await pg.wait_for_timeout(300)
            await ansicht_pruefen(pg, 'Kontomenue', meta)
            await pg.keyboard.press('Escape')
    else:
        await pg.click('[data-konto=anmelden]'); await pg.wait_for_timeout(500)
        await ansicht_pruefen(pg, 'Anmeldung', meta)
        await pg.fill('#access-dialog input[type=email], dialog[open] input[type=email]', 'falsch')
        await pg.click('dialog[open] button[type=submit]'); await pg.wait_for_timeout(500)
        await ansicht_pruefen(pg, 'Anmeldung mit Fehler', meta)
        await pg.keyboard.press('Escape')
    await ctx.close()

async def rechtsseiten(br, url, w, h):
    ctx = await br.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900)
    pg = await ctx.new_page(); meta = {'js': [], 'kontext': {'groesse': f'{w}x{h}', 'zustand': '-', 'sprache': 'de'}}
    pg.on('pageerror', lambda e: meta['js'].append(str(e)))
    for pfad, name in (('impressum.html', 'Impressum'), ('datenschutz.html', 'Datenschutz'), ('404.html', '404')):
        await pg.goto(url + pfad); await pg.wait_for_timeout(300)
        await ansicht_pruefen(pg, name, meta, erlaubt=('Fachkuerzel', 'S&P', 'Prozentzahl', 'Beispiel'), datenstand=99)
    await ctx.close()

async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in GROESSEN:
            for ein in (False, True):
                for sprache in ('de', 'en'):
                    try:
                        await lauf(br, url, w, h, ein, sprache)
                    except Exception as e:
                        befunde.append({'groesse': f'{w}x{h}', 'zustand': 'ein' if ein else 'aus', 'sprache': sprache, 'ansicht': 'Ablauf', 'befund': 'Testablauf abgebrochen: ' + str(e).split('\n')[0][:160]})
            await rechtsseiten(br, url, w, h)
            print(f'{w}x{h}: bisher {len(befunde)} Befunde', flush=True)
        await br.close()
    json.dump(befunde, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
    zus = collections.defaultdict(set)
    for b in befunde:
        zus[(b['ansicht'], b['befund'])].add(f"{b['groesse']} {b['zustand']} {b['sprache']}")
    for (a, f), wo in sorted(zus.items()):
        print(f'[{a}] {f}  ({len(wo)}×: {", ".join(sorted(wo)[:4])}{" …" if len(wo) > 4 else ""})')
    print('BEFUNDE:', len(zus))

asyncio.run(main())
