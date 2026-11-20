"""Verlauf (#verlauf): alle Zeitraeume, Verdichtung, Endpunkt, Baender, Chips, Ereigniskarte, ausgeloggt bis zum oeffentlichen Datum."""
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
async def main():
    srv, url = harness.starten()
    oeff = harness.stress_json()['publicSnapshot']['asOf']
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in ((390, 844), (1280, 860)):
            for ein in (False, True):
                ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=2)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                harness.ZUSTAND['aufrufe'].clear()
                await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1200)
                tag = '%d_%s' % (w, 'ein' if ein else 'aus')
                vorher = [a for a in harness.ZUSTAND['aufrufe'] if a[1] == '/api/historie']
                pruefe(not vorher, f'{tag}: voller Verlauf nicht auf der Startseite geladen')
                await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
                for sp in ('1M', '3M', '1J', '5J', 'A'):
                    await pg.click('[data-spanne="%s"]' % sp); await pg.wait_for_timeout(500)
                    r = await pg.evaluate("""()=>{const svg=document.querySelector('#verlauf-ansicht .verlauf-svg');const lin=svg.querySelector('.verlauf-linie');
                      const pts=lin.getAttribute('points').trim().split(' ').map(s=>s.split(',').map(Number));const last=pts[pts.length-1];
                      const c=svg.querySelector('.verlauf-endpunkt'),t=svg.querySelector('.verlauf-endwert');
                      const tb=t.getBBox(),vb=svg.viewBox.baseVal;
                      return {n:pts.length,end:[+c.getAttribute('cx'),+c.getAttribute('cy')],last,endText:t.textContent,txtRight:tb.x+tb.width,vbW:vb.width,
                        baender:svg.querySelectorAll('.verlauf-band').length,flaeche:!!svg.querySelector('.verlauf-flaeche'),
                        marken:[...svg.querySelectorAll('text.chart-text[text-anchor=middle]')].map(x=>x.textContent),
                        karte:!document.querySelector('#verlauf-ansicht .ereignis-karte')?.hidden,
                        gesperrt:!!document.querySelector('.verlauf-gesperrt')}}""")
                    pruefe(abs(r['end'][0] - r['last'][0]) < 0.2 and abs(r['end'][1] - r['last'][1]) < 0.2, f'{tag} {sp}: Endpunkt auf letztem Wert')
                    pruefe(r['txtRight'] <= r['vbW'] + 0.5, f'{tag} {sp}: Endwert {r["endText"]} innerhalb ({r["txtRight"]:.0f}/{r["vbW"]:.0f})')
                    if sp == '1M': pruefe(18 <= r['n'] <= 23 and not r['flaeche'], f'{tag} 1M: Tageswerte (n={r["n"]})')
                    if sp == '1J': pruefe(50 <= r['n'] <= 54 and not r['flaeche'], f'{tag} 1J: Wochenwerte ohne Spanne (n={r["n"]})')
                    if sp == 'A': pruefe(not r['flaeche'] and r['n'] > 200 and all(m.isdigit() for m in r['marken']), f'{tag} Alle: Monatswerte ohne Spanne (n={r["n"]}), Jahresmarken {r["marken"][:4]}')
                    if SHOT and sp in ('1M', '1J', 'A'): await pg.screenshot(path=str(SHOT / f'verlauf_{tag}_{sp}.png'))
                d = await pg.evaluate("fetch(%s).then(r=>r.json())" % json.dumps('/api/historie-oeffentlich'))
                letzt = await pg.evaluate("()=>{const t=document.querySelector('.verlauf-endwert');return t&&t.textContent}")
                o = await pg.evaluate("({fussnote:!!document.querySelector('#verlauf-ansicht .chart-note'),legende:!!document.querySelector('#verlauf-ansicht .verlauf-legende'),info:!!document.querySelector('.verlauf-info')})")
                pruefe(not o['fussnote'] and not o['legende'] and o['info'], f'{tag}: keine Fussnote, keine Legende, Info-Symbol am Titel {o}')
                await pg.click('.verlauf-info'); await pg.wait_for_timeout(200)
                it = await pg.evaluate("document.querySelector('#verlauf-info-text:not([hidden])')?.textContent||''")
                pruefe(it.startswith('Werte vor November 2026'), f'{tag}: Info-Text {it[:50]}')
                await pg.click('.verlauf-info'); await pg.wait_for_timeout(150)
                pruefe(r['gesperrt'] == (not ein), f'{tag}: Hinweis "Neuere Werte nach der Anmeldung" nur ausgeloggt')
                geladen = [a for a in harness.ZUSTAND['aufrufe'] if a[1] in ('/api/historie', '/api/historie-oeffentlich')]
                pruefe(any(a[1] == ('/api/historie' if ein else '/api/historie-oeffentlich') for a in geladen), f'{tag}: richtiger Endpunkt geladen')
                # Ereignis waehlen
                if w < 760:
                    await pg.click('[data-spanne="5J"]'); await pg.wait_for_timeout(400)
                    chips = await pg.evaluate("""()=>{const c=document.querySelector('.verlauf-chips');if(!c)return null;const a=c.querySelector('[aria-pressed=true]').getBoundingClientRect(),r=c.getBoundingClientRect();return {rand:c.className,inSicht:a.left>=r.left-1&&a.right<=r.right+1}}""")
                    pruefe(chips and chips['inSicht'] and 'rand' in chips['rand'], f'{tag}: Chip-Leiste mit Randverlauf, aktiver Chip in Sicht {chips}')
                    await pg.click('.verlauf-chip:last-child'); await pg.wait_for_timeout(400)
                k = await pg.evaluate("document.querySelector('#verlauf-ansicht .ereignis-karte').innerText")
                pruefe('Höchster Marktstress' in k and 'Wieder unter 40' in k and 'mit der KI einordnen' in k and 'Frag die KI' not in k and 'folgt' not in k, f'{tag}: Ereigniskarte vollstaendig ohne Beschreibung')
                pruefe(not js, f'{tag}: keine JS-Fehler {js}')
                await ctx.close()
        # Tooltip (zwei Zeilen) und Ereignis-Beschriftungen bei Alle/5J: Regel >= 70 bei Alle, keine Ueberlappung, nichts abgeschnitten
        for w, h in ((390, 844), (768, 1024), (1280, 860), (1440, 900)):
            for sprache in ('de', 'en'):
                ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=2 if SHOT else 1)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []; kons = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                pg.on('console', lambda m: kons.append(m.text) if m.type == 'error' else None)
                await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1500)
                if sprache == 'en': await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300)
                await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
                tag = f'{w} {sprache}'
                for sp in ('1M', '1J', '5J', 'A'):
                    await pg.click('[data-spanne="%s"]' % sp); await pg.wait_for_timeout(500)
                    box = await pg.locator('#verlauf-ansicht .verlauf-svg').bounding_box()
                    await pg.mouse.move(box['x'] + box['width'] * 0.45, box['y'] + box['height'] * 0.5); await pg.wait_for_timeout(200)
                    tip = await pg.evaluate("(()=>{const t=document.querySelector('.verlauf-tip');return t.hidden?null:[...t.children].map(x=>x.textContent)})()")
                    if w < 760 and not tip:
                        await pg.locator('#verlauf-ansicht .verlauf-diagramm').focus(); await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(150)
                        tip = await pg.evaluate("(()=>{const t=document.querySelector('.verlauf-tip');return t.hidden?null:[...t.children].map(x=>x.textContent)})()")
                    wert = 'Market stress ' if sprache == 'en' else 'Marktstress '
                    verboten = ('zurück', 'zum Schluss', 'aufgezeichnet', 'Bestandteile', 'back-calculated', 'recorded', 'at close', 'components')
                    pruefe(tip and len(tip) == 2 and tip[1].startswith(wert) and tip[1][len(wert):].isdigit() and not any(v in ' '.join(tip) for v in verboten), f'{tag} {sp}: Tooltip zwei Zeilen {tip}')
                    if sp == 'A' and tip: pruefe(len(tip[0].split()) == 2 and tip[0].split()[1].isdigit(), f'{tag} Alle: Tooltip Monat Jahr "{tip[0]}"')
                    if sp == '1M' and tip: pruefe(sum(x.strip('.,').isdigit() for x in tip[0].split()) == 2 and tip[0].split()[-1].isdigit(), f'{tag} 1M: Tooltip Tagesdatum "{tip[0]}"')
                    if sp in ('5J', 'A'):
                        r = await pg.evaluate("""()=>{const svg=document.querySelector('#verlauf-ansicht .verlauf-svg'),vb=svg.viewBox.baseVal;
                          const l=[...svg.querySelectorAll('.verlauf-band-text')].map(t=>{const b=t.getBBox();return {id:t.dataset.label,x:b.x,y:b.y,r:b.x+b.width,u:b.y+b.height}});
                          return {l,vbW:vb.width,baender:[...svg.querySelectorAll('.verlauf-band')].map(x=>x.dataset.band)}}""")
                        l = r['l']
                        ueber = [(a['id'], c['id']) for i, a in enumerate(l) for c in l[i+1:] if a['x'] < c['r'] and c['x'] < a['r'] and a['y'] < c['u'] - 2 and c['y'] < a['u'] - 2]
                        rand = [a['id'] for a in l if a['x'] < 30 or a['r'] > r['vbW'] - 34 + 0.5]
                        pruefe(not ueber and not rand, f'{tag} {sp}: Beschriftungen ohne Ueberlappung/Abschneiden ({len(l)} von {len(r["baender"])}) {ueber} {rand}')
                        pruefe((w < 760) == (len(l) == 0), f'{tag} {sp}: Beschriftungen nur Desktop ({len(l)})')
                    if SHOT and sprache == 'de' and sp == 'A': await pg.screenshot(path=str(SHOT / f'verlauf_alle_{w}.png'))
                    if SHOT and sprache == 'de' and sp == '5J' and w in (390, 1280): await pg.screenshot(path=str(SHOT / f'verlauf_5j_{w}.png'))
                    if SHOT and sp == 'A' and w in (390, 1280):
                        await pg.mouse.move(box['x'] + box['width'] * 0.30, box['y'] + box['height'] * 0.5); await pg.wait_for_timeout(200)
                        await pg.locator('#verlauf-ansicht .verlauf-diagramm').screenshot(path=str(SHOT / f'tooltip_{w}_{sprache}.png'))
                pruefe(not js and not kons, f'{tag}: keine JS-/Konsolenfehler {js} {kons}')
                await ctx.close()
        # Regel >= 70 bei Alle direkt an den Daten
        hd = harness.HIST()
        klein = [e['id'] for e in hd['ereignisse'] if e['spitze']['w'] < 70]
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}); await harness.supabase_route(ctx); pg = await ctx.new_page()
        await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1500)
        await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1500)
        await pg.click('[data-spanne="A"]'); await pg.wait_for_timeout(500)
        ids = await pg.evaluate("[...document.querySelectorAll('#verlauf-ansicht .verlauf-band')].map(x=>x.dataset.band)")
        pruefe(klein and not set(ids) & set(klein) and len(ids) == len(hd['ereignisse']) - len(klein), f'Alle: ohne Phasen unter 70 {klein}, gezeigt {len(ids)}')
        await ctx.close()
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
