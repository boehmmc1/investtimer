"""Updates der installierten Web-App: alter Build (A) -> neuer Build (B). Service Worker erkennt B, Seite laedt neu
(ruhig) bzw. zeigt "Neue Version verfuegbar" (KI-Eingabe offen); offline letzte Fassung mit "Offline · Stand"."""
import asyncio, os, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[2]
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
def bauen(ziel, version):
    shutil.copytree(ROOT / 'public', ziel, dirs_exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/build_v12.py'), str(ROOT / 'source/InvestTimer_UI_Signalbogen_v1.3.html'), str(ziel),
                    '--anmeldung=' + str(ROOT / 'deploy/supabase.json')], check=True, capture_output=True, env=dict(os.environ, IT_BUILD_VERSION=version))
async def main():
    tmp = Path(tempfile.mkdtemp()); a, b, live = tmp / 'A', tmp / 'B', tmp / 'live'
    bauen(a, '2026.11.19-0001'); bauen(b, '2026.11.19-0002')
    print('Versionen:', (a / 'version.json').read_text().strip(), '->', (b / 'version.json').read_text().strip())
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for fall in ('ruhig', 'gespraech'):
            shutil.rmtree(live, ignore_errors=True); shutil.copytree(a, live)
            srv, url = harness.starten(live)
            ctx = await br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
            await harness.supabase_route(ctx)
            pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1500)
            await pg.wait_for_function("navigator.serviceWorker.controller!==null", timeout=10000)
            await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(800)
            v = await pg.evaluate("document.querySelector('.konto-version')?.textContent")
            pruefe('0001' in (v or ''), f'{fall}: alter Build aktiv ({v})')
            if fall == 'gespraech':
                await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(600)
                await pg.fill('#ki-eingabe', 'Halb getippte Frage')
            shutil.copytree(b, live, dirs_exist_ok=True)   # Deploy des neuen Builds
            await pg.evaluate("window.InvestTimer.updatePruefen()")
            if fall == 'ruhig':
                try:
                    await pg.wait_for_event('load', timeout=15000)
                except Exception:
                    pass
                await pg.wait_for_timeout(1500)
                await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(800)
                v = await pg.evaluate("document.querySelector('.konto-version')?.textContent")
                pruefe('0002' in (v or ''), f'ruhig: automatisch neu geladen, neuer Build aktiv ({v})')
                # Offline: letzte Fassung aus dem Service Worker
                # Netz weg: Server anhalten (Playwrights Offline-Modus greift nicht fuer Anfragen des Service Workers)
                srv.shutdown(); srv.server_close()
                await pg.goto(url); await pg.wait_for_timeout(2500)
                r = await pg.evaluate("({wert:document.querySelector('.score')?.textContent.trim(),leiste:document.querySelector('.it-hinweisleiste:not([hidden])')?.textContent||''})")
                pruefe(r['wert'] and r['wert'] != '—' and r['leiste'].startswith('Offline · Stand'), f'offline: letzte Fassung mit Wert {r["wert"]} und "{r["leiste"]}"')
                port = int(url.rsplit(':', 1)[1].strip('/'))
                srv, _ = harness.starten(live, port)
                await pg.evaluate("window.InvestTimer.loadLive(true)"); await pg.wait_for_timeout(1500)
                pruefe(await pg.evaluate("document.querySelector('.it-hinweisleiste').hidden"), 'wieder online: Hinweis verschwindet')
            else:
                await pg.wait_for_timeout(4000)
                r = await pg.evaluate("({leiste:document.querySelector('.it-hinweisleiste:not([hidden])')?.textContent||'',eingabe:document.querySelector('#ki-eingabe')?.value})")
                pruefe('Neue Version verfügbar' in r['leiste'] and r['eingabe'] == 'Halb getippte Frage', f'gespraech: kein Neuladen, Hinweis "{r["leiste"]}", Eingabe erhalten')
                await pg.click('[data-update=jetzt]'); await pg.wait_for_timeout(2500)
                await pg.evaluate("location.hash='konto'"); await pg.wait_for_timeout(800)
                v = await pg.evaluate("document.querySelector('.konto-version')?.textContent")
                pruefe('0002' in (v or ''), f'gespraech: "Aktualisieren" laedt neuen Build ({v})')
            caches = await pg.evaluate("caches.keys()")
            pruefe(all('0001' not in c for c in caches), f'{fall}: alte Caches geloescht {caches}')
            pruefe(not js, f'{fall}: keine JS-Fehler {js}')
            await ctx.close(); srv.shutdown()
        await br.close()
    shutil.rmtree(tmp)
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
