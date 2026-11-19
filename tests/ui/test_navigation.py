"""Navigation: vier Ansichten mit eigener URL, Zurueck-Taste, Konto-Ansicht ein-/ausgeloggt, Desktop-Kontomenue."""
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
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for ein in (False, True):
            ctx = await b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
            await harness.supabase_route(ctx)
            pg = await ctx.new_page(); js = []
            pg.on('pageerror', lambda e: js.append(str(e)))
            await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1200)
            tag = 'ein' if ein else 'aus'
            for ziel, sel in (('ki', '#ki-ansicht'), ('verlauf', '#verlauf-ansicht'), ('konto', '#konto-ansicht')):
                await pg.tap('.it-leiste [data-ziel=%s]' % ziel); await pg.wait_for_timeout(700)
                h = await pg.evaluate('location.hash')
                sicht = await pg.evaluate("s=>{const e=document.querySelector(s);return !!e&&!e.hidden&&e.getBoundingClientRect().height>50}", sel)
                main_weg = await pg.evaluate("getComputedStyle(document.querySelector('.app>main')).display==='none'")
                cur = await pg.evaluate("document.querySelector('.it-leiste [aria-current=page]')?.dataset.ziel")
                pruefe(h == '#' + ziel and sicht and main_weg and cur == ziel, f'{tag} Tab {ziel}: hash={h} sichtbar={sicht} main weg={main_weg} aktiv={cur}')
                if SHOT: await pg.screenshot(path=str(SHOT / f'nav_{ziel}_{tag}.png'))
            await pg.go_back(); await pg.wait_for_timeout(500)
            pruefe(await pg.evaluate('location.hash') == '#verlauf' and await pg.evaluate("!document.querySelector('#verlauf-ansicht').hidden"), f'{tag} Zurueck -> #verlauf')
            await pg.tap('.it-leiste [data-ziel=stress]'); await pg.wait_for_timeout(500)
            pruefe(await pg.evaluate("location.hash===''&&getComputedStyle(document.querySelector('.app>main')).display!=='none'"), f'{tag} Tab Marktstress zurueck zur Startseite')
            await pg.go_back(); await pg.wait_for_timeout(500)
            pruefe(await pg.evaluate('location.hash') == '#verlauf', f'{tag} Zurueck nach Marktstress -> #verlauf')
            await pg.goto(url + '#konto'); await pg.wait_for_timeout(1200)
            txt = await pg.evaluate("document.querySelector('#konto-ansicht').innerText")
            if ein:
                for w in ('test@investtimer.net', 'Registriert seit', '16. November 2026', 'Meine Alarme', 'Steigt über 60', 'wartet', 'pausiert', 'Sprache', 'E-Mail-Adresse ändern', 'Meine Daten herunterladen', 'Überall abmelden', 'Konto löschen', 'Abmelden', 'Impressum', 'Datenschutz', 'Version'):
                    pruefe(w.lower() in txt.lower(), f'ein Konto enthaelt "{w}"')
                pruefe('Abo' not in txt.split('Mein Konto')[0], 'ein Konto: kein Abo-Block ohne Paywall')
                await pg.tap('.konto-alarm'); await pg.wait_for_timeout(500)
                pruefe(await pg.evaluate("!!document.querySelector('#alarm-dialog[open]')"), 'ein Konto: Tippen auf Alarm oeffnet Dialog')
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
                await pg.select_option('#konto-sprache', 'en'); await pg.wait_for_timeout(400)
                pruefe(await pg.evaluate("document.documentElement.lang") == 'en' and 'Member since' in await pg.evaluate("document.querySelector('#konto-ansicht').innerText"), 'ein Sprache in der Konto-Ansicht wechselt auf EN')
                await pg.select_option('#konto-sprache', 'de'); await pg.wait_for_timeout(300)
                pruefe(await pg.evaluate("getComputedStyle(document.querySelector('#konto-knopf')).borderTopWidth") == '0px', 'ein Kontoknopf ohne eckigen Rahmen')
                await pg.tap('#konto-knopf'); await pg.wait_for_timeout(300)
                pruefe(await pg.evaluate("location.hash") == '#konto', 'ein mobil: Initialen-Kreis fuehrt nach #konto')
            else:
                for w in ('Melde dich an', 'Anmelden', 'Sprache', 'Impressum', 'Datenschutz'):
                    pruefe(w.lower() in txt.lower(), f'aus Konto enthaelt "{w}"')
                await pg.tap('[data-konto=anmelden]'); await pg.wait_for_timeout(400)
                pruefe(await pg.evaluate("!!document.querySelector('dialog[open]')"), 'aus Konto: Anmelden oeffnet Anmeldedialog')
            pruefe(await pg.evaluate("getComputedStyle(document.querySelector('#header-language')).display") == 'none', f'{tag} mobil: Sprachwahl nicht im Header')
            pruefe(not js, f'{tag} keine JS-Fehler {js}')
            await ctx.close()
        # Desktop
        ctx = await b.new_context(viewport={'width': 1280, 'height': 860})
        await harness.supabase_route(ctx)
        pg = await ctx.new_page(); js = []
        pg.on('pageerror', lambda e: js.append(str(e)))
        await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1200)
        tabs = await pg.evaluate("[...document.querySelectorAll('.it-tabs a')].map(a=>a.textContent)")
        pruefe(tabs == ['Marktstress', 'KI', 'Verlauf'], f'Desktop Tabs {tabs}')
        await pg.click('#konto-knopf'); await pg.wait_for_timeout(300)
        await pg.click('[data-km=konto]'); await pg.wait_for_timeout(600)
        pruefe(await pg.evaluate("location.hash==='#konto'&&!document.querySelector('#konto-ansicht').hidden"), 'Desktop: Mein Konto fuehrt auf #konto')
        await pg.click('.it-tabs [data-ziel=verlauf]'); await pg.wait_for_timeout(1200)
        pruefe(await pg.evaluate("location.hash==='#verlauf'&&!!document.querySelector('#verlauf-ansicht svg.verlauf-svg')"), 'Desktop: Verlauf-Tab zeigt Chart')
        if SHOT: await pg.screenshot(path=str(SHOT / 'nav_desktop_verlauf.png'))
        pruefe(not js, f'Desktop keine JS-Fehler {js}')
        await b.close()
    print('FEHLER:', len(fehler))
    return 1 if fehler else 0
sys.exit(asyncio.run(main()))
