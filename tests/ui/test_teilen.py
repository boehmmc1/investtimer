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
        # Kompakter Knopf: Symbol + "Teilen", 13-14 px, Sekundaerfarbe, ohne Rahmen/Hintergrund, Klickflaeche >= 44 px;
        # Startseite in der Stufen-Zeile, Verlauf in der Zeitraum-Zeile (kein Umbruch), Ereigniskarte oben rechts
        STIL = """b=>{const s=getComputedStyle(b),r=b.getBoundingClientRect();return {text:b.innerText.trim(),fs:parseFloat(s.fontSize),farbe:s.color,
            rahmen:s.borderTopWidth,bg:s.backgroundColor,h:r.height,w:r.width,top:r.top,bottom:r.bottom,left:r.left,right:r.right,mitte:(r.top+r.bottom)/2}}"""
        for w, h in ((320, 568), (390, 844), (1280, 860)):
            for sp in ('de', 'en'):
                for ein in (False, True):
                    harness.ZUSTAND['teilen_aktuell'] = False
                    ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 760, has_touch=w < 760)
                    await harness.supabase_route(ctx)
                    pg = await ctx.new_page(); js = []
                    pg.on('pageerror', lambda e: js.append(str(e)))
                    await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1300)
                    if sp == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
                    tag = f'{w} {sp} {"ein" if ein else "aus"}'
                    wort = 'Share' if sp == 'en' else 'Teilen'
                    k = await pg.evaluate("(STIL)=>{const f=eval(STIL),b=document.querySelector('.status-zeile .teilen-knopf'),st=document.querySelector('#status');return b&&st?{k:f(b),st:f(st),sub:getComputedStyle(document.body).getPropertyValue('--sub')}:null}", STIL)
                    pruefe(k and k['k']['text'] == wort and 13 <= k['k']['fs'] <= 14 and k['k']['rahmen'] == '0px' and k['k']['bg'] in ('rgba(0, 0, 0, 0)', 'transparent')
                           and k['k']['h'] >= 44 and k['k']['w'] >= 44 and abs(k['k']['mitte'] - k['st']['mitte']) < 6, f'{tag}: Startseite kompakter Knopf in der Stufen-Zeile {k and (k["k"]["text"], k["k"]["fs"], round(k["k"]["mitte"] - k["st"]["mitte"]))}')
                    await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1400)
                    v = await pg.evaluate("(STIL)=>{const f=eval(STIL),b=document.querySelector('.verlauf-kopf .teilen-knopf'),z=[...document.querySelectorAll('.verlauf-spanne')];return b?{k:f(b),z:z.map(f),vw:innerWidth,sw:document.documentElement.scrollWidth}:null}", STIL)
                    gleiche_zeile = v and all(abs(x['mitte'] - v['k']['mitte']) < 4 for x in v['z'])
                    pruefe(v and gleiche_zeile and v['k']['right'] <= v['vw'] and v['sw'] <= v['vw'] and v['k']['left'] >= max(x['right'] for x in v['z'])
                           and v['k']['h'] >= 44 and (v['k']['text'] in (wort, '')), f'{tag}: Verlauf-Knopf in der Zeitraum-Zeile ohne Umbruch {v and (v["k"]["text"], round(v["k"]["left"]), round(v["k"]["right"]), v["vw"])}')
                    kk = await pg.evaluate("(STIL)=>{const f=eval(STIL),c=document.querySelector('#verlauf-ansicht .ereignis-karte'),b=c&&c.querySelector('.karte-kopf .teilen-knopf'),h=c&&c.querySelector('h4');if(!b)return null;const r=c.getBoundingClientRect();return {k:f(b),h4:f(h),karte:{right:r.right,top:r.top}}}", STIL)
                    pruefe(kk and kk['k']['right'] <= kk['karte']['right'] and kk['karte']['right'] - kk['k']['right'] < 24 and kk['k']['top'] - kk['karte']['top'] < 20
                           and kk['k']['right'] > kk['h4']['right'], f'{tag}: Ereigniskarte Knopf oben rechts')
                    pruefe(not js, f'{tag}: keine JS-Fehler {js[:2]}')
                    if SHOT and sp == 'de' and not ein:
                        await pg.screenshot(path=str(SHOT / f'teilen2_verlauf_{w}.png'))
                        await pg.evaluate("history.pushState(null,'',location.pathname);dispatchEvent(new PopStateEvent('popstate'))"); await pg.wait_for_timeout(600)
                        await pg.screenshot(path=str(SHOT / f'teilen2_start_{w}.png'))
                    await ctx.close()
        # Eingeloggt mit IT_TEILEN_AKTUELL: aktueller Wert, Stand mit Uhrzeit, Link mit Zeitstempel; Werte ueberall gleich
        harness.ZUSTAND.update(teilen_aktuell=True, wert=77)
        ctx = await b.new_context(viewport={'width': 1280, 'height': 860}); await harness.supabase_route(ctx)
        await ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=url.rstrip('/'))
        pg = await ctx.new_page(); js = []
        pg.on('pageerror', lambda e: js.append(str(e)))
        await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1500)
        harness.ZUSTAND['teilen_bild'] = []
        await pg.click('.status-zeile .teilen-knopf'); await pg.wait_for_timeout(1200)
        d = await pg.evaluate(DIALOG_JS)
        pruefe(d and '77 von 100 (Hoch)' in d['text'] and '· Stand 20. Nov. 2026, 15:34' in d['text'] and '/s/wert/2026-11-20T1534' in d['kopieren']
               and any('aktuell=1' in x for x in harness.ZUSTAND['teilen_bild']), f'eingeloggt: aktueller Wert mit Uhrzeit und Zeitstempel-Link "{d and d["text"]}"')
        await pg.keyboard.press('Escape')
        start = await pg.evaluate("document.querySelector('.score')?.textContent?.trim()||document.querySelector('#score')?.textContent?.trim()")
        werte = {}
        await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
        for sp_ in ('1M', '3M', '1J', '5J', 'A'):
            await pg.click('[data-spanne="%s"]' % sp_); await pg.wait_for_timeout(400)
            werte[sp_] = await pg.evaluate("document.querySelector('.verlauf-endwert')?.textContent")
        await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(900)
        ki = await pg.evaluate("document.querySelector('#ki-ansicht').innerText")
        await pg.evaluate("history.pushState(null,'',location.pathname);dispatchEvent(new PopStateEvent('popstate'))"); await pg.wait_for_timeout(700)
        bruecke = await pg.evaluate("[...document.querySelectorAll('.ki-bruecke-start, .ki-bruecke-knopf, .ki-bruecke')].map(x=>x.innerText).join(' ')")
        pruefe(all(x == '77' for x in werte.values()) and 'HEUTE 77' in ki.upper() and 'hinter der 77' in bruecke, f'Werte ueberall gleich: Verlauf-Endpunkte {werte}, KI-Eyebrow, KI-Bruecke ({start})')
        pruefe(not js, f'eingeloggt aktuell: keine JS-Fehler {js[:2]}')
        await ctx.close()
        harness.ZUSTAND.update(teilen_aktuell=False, wert=None)
        # Landeseite eines geteilten Links (ausgeloggt): Band mit Wert, Stufe, Stand; Registrieren; schliessbar
        for sp, ziel_, text in (('de', '?geteilt=wert&st=%s&utm_source=teilen&utm_medium=x' % STAND, 'Geteilt: Marktstress %d (' % MANI['wert']),
                                ('en', '?geteilt=wert&st=%s&lang=en&utm_source=teilen&utm_medium=x' % STAND, 'Shared: market stress %d (' % MANI['wert'])):
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True); pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            await pg.goto(url + ziel_); await pg.wait_for_timeout(2000)
            band = await pg.evaluate("document.querySelector('.geteilt-band')?.innerText||''")
            pruefe(text in band and ('Kostenlos registrieren' in band or 'Sign up free' in band), f'Band {sp}: "{band[:90]}"')
            if SHOT and sp == 'de': await pg.screenshot(path=str(SHOT / 'teilen2_band_390.png'))
            await pg.click('[data-band-registrieren]'); await pg.wait_for_timeout(700)
            reg = await pg.evaluate("document.querySelector('#access-dialog[open], dialog[open]')?.innerText||''")
            pruefe(('Konto anlegen' in reg) if sp == 'de' else ('Create your account' in reg), f'Band {sp}: Registrieren oeffnet den Dialog "{reg[:60]}"')
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
            await pg.click('[data-band-zu]'); await pg.wait_for_timeout(200)
            pruefe(await pg.evaluate("!document.querySelector('.geteilt-band')"), f'Band {sp}: schliessbar')
            pruefe(not js, f'Band {sp}: keine JS-Fehler {js[:2]}')
            await ctx.close()
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
