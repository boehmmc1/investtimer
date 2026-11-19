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
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
