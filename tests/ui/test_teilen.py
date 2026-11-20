"""Teilen: Knoepfe (Startseite, Verlauf, Ereigniskarte, mind. 44 px), Dialog (Bild, Download, Link kopieren, WhatsApp/LinkedIn/X/Threads
nur als einfache Adressen), natives Teilen mit Datei (mobil), Ankunft ueber geteilte Links (Zeitraum, Phase, Sprache, Zaehlung ohne Kennung,
Adresse bereinigt), ausgeloggt und eingeloggt, DE/EN. Screenshots nach <ordner>."""
import asyncio, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
MANI = json.loads((Path('/var/lib/investtimer/teilen/aktuell/manifest.json')).read_text())
STAND = MANI['asOf']
DIALOG_JS = """()=>{const d=document.querySelector('.teilen-dialog');if(!d||!d.open)return null;const i=d.querySelector('.teilen-bild');
 return {bild:i?i.getAttribute('src'):'',breite:i?i.naturalWidth:0,text:d.querySelector('.teilen-text')?.textContent||'',
  netze:[...d.querySelectorAll('.teilen-netz')].map(a=>[a.textContent,a.href,a.target,a.rel]),
  laden:[...d.querySelectorAll('a[download]')].map(a=>a.getAttribute('href')),kopieren:d.querySelector('[data-kopieren]')?.dataset.kopieren||'',
  skripte:[...document.scripts].filter(s=>s.src&&!s.src.startsWith(location.origin)).length}}"""
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h, ein, sp in ((1280, 860, False, 'de'), (1280, 860, True, 'en'), (390, 844, False, 'de'), (390, 844, True, 'de')):
            mobil = w < 760
            ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=mobil, has_touch=mobil, device_scale_factor=2 if SHOT else 1)
            await ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=url.rstrip('/'))
            await harness.supabase_route(ctx)
            pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            pg.on('console', lambda m: js.append(m.text) if m.type == 'error' else None)
            if mobil:
                await pg.add_init_script("""window.__geteilt=[];navigator.canShare=()=>true;navigator.share=d=>{window.__geteilt.push({name:d.files&&d.files[0]&&d.files[0].name,typ:d.files&&d.files[0]&&d.files[0].type,groesse:d.files&&d.files[0]&&d.files[0].size,text:d.text});return Promise.resolve()}""")
            await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1300)
            if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
            tag = f'{w} {"ein" if ein else "aus"} {sp}'
            k = pg.locator('.teilen-start .teilen-knopf')
            box = await k.bounding_box() if await k.count() else None
            pruefe(box and box['height'] >= 44 and await k.is_visible(), f'{tag}: Teilen-Knopf auf der Startseite ({box and round(box["height"])} px) "{await k.inner_text() if await k.count() else ""}"')
            if SHOT and not ein and sp == 'de': await pg.screenshot(path=str(SHOT / f'teilen_start_{w}.png'))
            harness.ZUSTAND['ansichten'].clear()
            await k.click(); await pg.wait_for_timeout(1200)
            if mobil:
                g = await pg.evaluate("window.__geteilt")
                pruefe(len(g) == 1 and g[0]['name'] == 'investtimer-wert.png' and g[0]['typ'] == 'image/png' and g[0]['groesse'] > 10000
                       and '/s/wert/' + STAND in g[0]['text'] and 'utm_medium=nativ' in g[0]['text'], f'{tag}: natives Teilen mit Bild und Link {g}')
                pruefe(any('a=teilen-wert-nativ' in a for a in harness.ZUSTAND['ansichten']), f'{tag}: Zaehlung teilen-wert-nativ')
            else:
                d = await pg.evaluate(DIALOG_JS)
                pruefe(d and d['bild'].endswith('/wert-quer-%s.png' % sp) and d['breite'] == 1200, f'{tag}: Dialog mit Bild {d and d["bild"]} ({d and d["breite"]} px)')
                pruefe(d and [n[0] for n in d['netze']] == ['WhatsApp', 'LinkedIn', 'X', 'Threads'] and all(n[2] == '_blank' and 'noopener' in n[3] for n in d['netze'])
                       and d['netze'][0][1].startswith('https://wa.me/') and 'linkedin.com/sharing/share-offsite' in d['netze'][1][1]
                       and d['netze'][2][1].startswith('https://x.com/intent/post') and 'threads.net/intent/post' in d['netze'][3][1], f'{tag}: vier Netzwerke als einfache Adressen')
                pruefe(d and d['skripte'] == 0, f'{tag}: keine fremden Skripte')
                pruefe(d and ('/s/wert/' + STAND) in d['kopieren'] and 'utm_source=teilen&utm_medium=link' in d['kopieren'] and (('l=en' in d['kopieren']) == (sp == 'en')),
                       f'{tag}: Link {d and d["kopieren"]}')
                pruefe(d and 'Anlage' not in d['text'] and ('Marktstress' in d['text'] or 'Market stress' in d['text']), f'{tag}: Text "{d and d["text"]}"')
                await pg.click('[data-kopieren]'); await pg.wait_for_timeout(300)
                kopiert = await pg.evaluate("navigator.clipboard.readText()")
                pruefe(kopiert == d['kopieren'], f'{tag}: Link kopiert')
                if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / f'teilen_dialog_wert_{w}.png'))
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
                pruefe(await pg.evaluate("!document.querySelector('.teilen-dialog').open&&document.activeElement.classList.contains('teilen-knopf')"), f'{tag}: Escape schliesst, Fokus zurueck')
                pruefe(any('a=teilen-wert' in a for a in harness.ZUSTAND['ansichten']) and all('@' not in a for a in harness.ZUSTAND['ansichten']), f'{tag}: Zaehlung ohne Kennung')
            # Verlauf: Knopf neben den Zeitraeumen, gewaehlter Zeitraum wird geteilt
            await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
            await pg.click('[data-spanne="5J"]'); await pg.wait_for_timeout(500)
            vk = pg.locator('.verlauf-kopf .teilen-knopf')
            r = await pg.evaluate("""()=>{const k=document.querySelector('.verlauf-kopf .teilen-knopf'),z=document.querySelector('.verlauf-knoepfe');if(!k)return null;
              const a=k.getBoundingClientRect(),c=z.getBoundingClientRect();return {h:a.height,rechts:a.right<=innerWidth+.5,ueber:!(a.left>=c.right||a.top>=c.bottom||a.bottom<=c.top)}}""")
            pruefe(r and r['h'] >= 44 and r['rechts'] and not r['ueber'], f'{tag}: Verlauf-Knopf {r}')
            await vk.click(); await pg.wait_for_timeout(1200)
            if mobil:
                g = await pg.evaluate("window.__geteilt")
                pruefe(g[-1]['name'] == 'investtimer-verlauf-5J.png' and '/s/verlauf/5J/' + STAND in g[-1]['text'], f'{tag}: Verlauf 5J nativ geteilt')
            else:
                d = await pg.evaluate(DIALOG_JS)
                pruefe(d and d['bild'].endswith('/verlauf-5J-quer-%s.png' % sp) and d['breite'] == 1200 and '/s/verlauf/5J/' + STAND in d['kopieren'], f'{tag}: Verlauf 5J im Dialog')
                if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / f'teilen_dialog_verlauf_{w}.png'))
                await pg.click('.teilen-zu'); await pg.wait_for_timeout(200)
            # Ereigniskarte
            pk = pg.locator('.ereignis-karte .teilen-knopf')
            pid = await pk.get_attribute('data-phase')
            pruefe(await pk.count() == 1 and (await pk.bounding_box())['height'] >= 44, f'{tag}: Knopf in der Ereigniskarte ({pid})')
            await pk.click(); await pg.wait_for_timeout(1200)
            if mobil:
                g = await pg.evaluate("window.__geteilt")
                pruefe(g[-1]['name'] == 'investtimer-phase-%s.png' % pid and '/s/phase/' + pid in g[-1]['text'], f'{tag}: Phase nativ geteilt')
                if SHOT and not ein: await pg.screenshot(path=str(SHOT / f'teilen_verlauf_{w}.png'))
            else:
                d = await pg.evaluate(DIALOG_JS)
                pruefe(d and d['bild'].endswith('/phase-%s-quer-%s.png' % (pid, sp)) and d['breite'] == 1200 and '/s/phase/' + pid in d['kopieren'], f'{tag}: Phase im Dialog')
                if SHOT and sp == 'de' and not ein: await pg.screenshot(path=str(SHOT / f'teilen_dialog_phase_{w}.png'))
                await pg.click('.teilen-zu')
            pruefe(not js, f'{tag}: keine JS-/Konsolenfehler {js[:3]}')
            await ctx.close()
        # Ankunft ueber geteilte Links
        for ziel, erwartet in (('?z=5J&utm_source=teilen&utm_medium=whatsapp#verlauf', {'spanne': '5J', 'm': 'whatsapp'}),
                               ('?phase=corona&utm_source=teilen&utm_medium=x#verlauf', {'spanne': 'A', 'phase': 'corona', 'm': 'x'}),
                               ('?phase=fruehjahr2026&utm_source=teilen&utm_medium=linkedin&lang=en#verlauf', {'spanne': '5J', 'phase': 'fruehjahr2026', 'm': 'linkedin', 'lang': 'en'}),
                               ('?utm_source=teilen&utm_medium=threads', {'m': 'threads'})):
            ctx = await b.new_context(viewport={'width': 1280, 'height': 860}); pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            harness.ZUSTAND['ansichten'].clear()
            await pg.goto(url + ziel); await pg.wait_for_timeout(2200)
            r = await pg.evaluate("""()=>({adresse:location.search,hash:location.hash,lang:document.documentElement.lang,
              spanne:document.querySelector('.verlauf-spanne.aktiv')?.dataset.spanne||null,
              phase:document.querySelector('#verlauf-ansicht .verlauf-chip[aria-pressed=true],#verlauf-ansicht .verlauf-band-knopf[aria-pressed=true]')?.dataset.ereignis||null})""")
            ok = r['adresse'] == '' and all(r.get(k) == v for k, v in erwartet.items() if k in ('spanne', 'phase', 'lang'))
            pruefe(ok and any('a=besuch-teilen-' + erwartet['m'] in a for a in harness.ZUSTAND['ansichten']), f'Ankunft {ziel}: {r}')
            pruefe(not js, f'Ankunft {ziel}: keine JS-Fehler {js[:2]}')
            await ctx.close()
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
