"""Start mit Sitzung: nie der oeffentliche/eingebettete Wert. Ohne gespeicherten Wert Platzhalter, dann einmal fuellen;
mit gespeichertem Wert sofort ohne Animation, dann gleiten; API haengt > 4 s: gespeicherter Wert bleibt mit Stand-Datum.
Ausgeloggt: zeitversetzter Wert wie bisher. Bildfolge des Starts nach <ordner>."""
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
OEFF = str(harness.stress_json()['publicSnapshot']['rounded'])
async def folge(pg, dauer_ms, name=None, schritt=100):
    werte = []
    for i in range(dauer_ms // schritt):
        z = await pg.evaluate("()=>{const s=document.querySelector('.gauge-stage .score');if(!s)return {t:'',v:'hidden',laedt:true,bogen:'',stamp:''};return {t:s?.textContent.trim(),v:getComputedStyle(s).visibility,laedt:document.body.classList.contains('wert-laedt'),bogen:document.querySelector('.gauge-value')?.style.strokeDasharray||'',stamp:document.querySelector('.snapshot-label')?.textContent||''}}")
        werte.append(z)
        if SHOT and name and i % 3 == 0: await pg.screenshot(path=str(SHOT / f'{name}_{i:02d}.png'), clip={'x': 0, 'y': 60, 'width': 390, 'height': 520})
        await pg.wait_for_timeout(schritt)
    return werte
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}); await harness.supabase_route(ctx)
        pg = await ctx.new_page()
        # 1) Erste Anmeldung, kein gespeicherter Wert, API antwortet nach 1,5 s (Wert 61)
        harness.ZUSTAND.update(wert=61, aktuell_verzoegerung=1.5)
        await pg.goto(url + harness.LOGIN_HASH)
        w = await folge(pg, 4000, 'start_ohne_speicher')
        sichtbar = [x['t'] for x in w if x['v'] == 'visible' and not x['laedt']]
        zahlen = [int(x) for x in sichtbar if x.isdigit()]
        pruefe(zahlen and all(a <= b for a, b in zip(zahlen, zahlen[1:])), f'ohne Speicher: oeffentlicher Wert {OEFF} nie sichtbar (sichtbar: {sorted(set(sichtbar))[:8]})')
        pruefe(w[0]['laedt'] and w[-1]['t'] == '61', 'ohne Speicher: erst Platzhalter, dann 61')
        # 2) Neustart (kalter Start): gespeichert 61, frisch 64 -> sofort 61 ohne Fuellen, dann gleiten auf 64
        harness.ZUSTAND.update(wert=64, aktuell_verzoegerung=1.2)
        await pg.goto('about:blank'); await pg.goto(url)
        w = await folge(pg, 3500, 'start_mit_speicher')
        pruefe(w[0]['t'] == '61' and not w[0]['laedt'], f'mit Speicher: sofort 61 ({w[0]})')
        ts = [x['t'] for x in w]
        pruefe(OEFF not in ts and all(t in [str(v) for v in range(61, 65)] for t in ts) and ts[-1] == '64', f'mit Speicher: nur 61..64, gleitet auf 64 ({sorted(set(ts))})')
        # 3) gleicher Wert: nichts bewegt sich
        await pg.goto('about:blank'); await pg.goto(url)
        w = await folge(pg, 2500)
        pruefe(len({x['t'] for x in w}) == 1 and len({x['bogen'] for x in w}) == 1, f'gleicher Wert: keine Bewegung ({ {x["t"] for x in w} })')
        # 4) API haengt > 4 s: gespeicherter Wert bleibt, Stand-Datum
        harness.ZUSTAND.update(wert=70, aktuell_verzoegerung=8)
        await pg.goto('about:blank'); await pg.goto(url)
        w = await folge(pg, 5000)
        pruefe(all(x['t'] == '64' for x in w) and w[-1]['stamp'].startswith('Stand'), f'API haengt: bleibt bei 64, "{w[-1]["stamp"]}"')
        harness.ZUSTAND.update(aktuell_verzoegerung=0)
        await pg.wait_for_timeout(4000)
        # 5) Abmelden entfernt den gespeicherten Wert
        await pg.evaluate("window.InvestTimer.abmelden()"); await pg.wait_for_timeout(500)
        pruefe(await pg.evaluate("localStorage.getItem('investtimer-aktuell')") is None, 'Abmelden entfernt den gespeicherten Wert')
        await ctx.close()
        # 6) Ausgeloggt: direkt der zeitversetzte Wert
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}); pg = await ctx.new_page()
        await pg.goto(url); w = await folge(pg, 2500)
        pruefe(w[-1]['t'] == OEFF and not any(x['laedt'] for x in w), f'ausgeloggt: zeitversetzter Wert {OEFF}')
        await ctx.close()
        # 7) Langsames Netz (Slow 4G, CDP-Drosselung), Sitzung ohne Speicher
        ctx = await br.new_context(viewport={'width': 390, 'height': 844}); await harness.supabase_route(ctx)
        pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 562, 'downloadThroughput': 180000, 'uploadThroughput': 84000})
        harness.ZUSTAND.update(wert=58)
        await pg.goto(url + harness.LOGIN_HASH, wait_until='commit')
        w = await folge(pg, 9000, 'start_slow4g', schritt=150)
        sichtbar = [x['t'] for x in w if x['v'] == 'visible' and not x['laedt'] and x['t'] not in ('', None)]
        zahlen = [int(x) for x in sichtbar if x.isdigit()]
        pruefe(zahlen and zahlen[-1] == 58 and all(a <= b for a, b in zip(zahlen, zahlen[1:])), f'Slow 4G: Zahl zaehlt einmal monoton bis 58, kein Ruecksprung/Zwischenwert ({zahlen[:12]})')
        await ctx.close(); await br.close()
    harness.ZUSTAND.update(wert=None, aktuell_verzoegerung=0)
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
