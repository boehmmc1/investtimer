"""Mobil-Pruefung vor jedem Push: Ueberlauf, Tippflaechen (mind. 40 px),
Eingabe-Schriftgroessen (mind. 16 px gegen iOS-Zoom), abgeschnittene Dialoge.
Prueft 6 Bildschirmgroessen x 9 Ansichten. Braucht playwright und Chrome.

Aufruf: python3 tools/check_mobile.py [--shots]     (Endet mit 1 bei Auffaelligkeiten)
"""
import asyncio, functools, http.server, json, os, sys, threading
from playwright.async_api import async_playwright

PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
SHOTS = '--shots' in sys.argv
VIEWPORTS = [(320, 568), (360, 740), (390, 844), (430, 932), (844, 390), (768, 1024)]

CHECK = """() => {
  const vw = document.documentElement.clientWidth, out = {overflow: document.documentElement.scrollWidth - vw, wide: [], small: [], zoom: [], clipped: []};
  const visible = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !el.closest('[hidden]') && !(el.closest('dialog') && !el.closest('dialog').open) && !(el.closest('details') && !el.closest('details').open && el.tagName !== 'SUMMARY' && !el.closest('summary')); };
  const label = el => (el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '')) ;
  const openDialog = document.querySelector('dialog[open]');
  for (const el of document.querySelectorAll('body *')) {
    if (!visible(el)) continue;
    if (openDialog && !openDialog.contains(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) out.wide.push(label(el) + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
    if (el.matches('button, a[href], select, input:not([type=range]):not([type=radio]):not([type=checkbox]), summary, label:has(input[type=radio]), label:has(input[type=checkbox])')) {
      if (r.height < 40 || r.width < 40) out.small.push(label(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
    }
    if (el.matches('input:not([type=range]):not([type=radio]):not([type=checkbox]), select, textarea') && parseFloat(getComputedStyle(el).fontSize) < 16) out.zoom.push(label(el) + ' ' + getComputedStyle(el).fontSize);
  }
  if (openDialog) { const r = openDialog.getBoundingClientRect(); if (r.bottom > innerHeight + 1 || r.top < -1) out.clipped.push(label(openDialog) + ' ' + Math.round(r.top) + '..' + Math.round(r.bottom) + ' von ' + innerHeight + ' scrollbar=' + (openDialog.scrollHeight > openDialog.clientHeight)); }
  out.wide = [...new Set(out.wide)].slice(0, 6); out.small = [...new Set(out.small)]; out.zoom = [...new Set(out.zoom)];
  return out;
}"""


async def main():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=PUBLIC)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    URL = 'http://127.0.0.1:%d/index.html' % server.server_address[1]
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
        totals = {}
        for w, h in VIEWPORTS:
            ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=w < 900, has_touch=True)
            pg = await ctx.new_page()
            errors = []
            pg.on('pageerror', lambda e: errors.append(str(e)))
            await pg.goto(URL)
            await pg.wait_for_timeout(500)

            async def state(name):
                await pg.wait_for_timeout(350)
                r = await pg.evaluate(CHECK)
                problems = {k: v for k, v in r.items() if v and v != 0 and not (k == 'overflow' and v <= 0)}
                if SHOTS:
                    await pg.screenshot(path=f'/tmp/a_{w}_{name}.png')
                if problems:
                    print(f'{w}x{h} {name}: {json.dumps(problems, ensure_ascii=False)}')
                for k, v in problems.items():
                    totals[k] = totals.get(k, 0) + (len(v) if isinstance(v, list) else 1)

            await state('start')
            await pg.click('#details-toggle'); await state('details')
            await pg.click('[data-perspective="volatility"] summary'); await state('perspektive')
            await pg.click('[data-explain="VIX_VX1"]'); await state('erklaerung')
            await pg.click('#understood')
            await pg.click('#create-alert'); await state('alarm')
            await pg.click('#close-alert')
            await pg.evaluate('window.scrollTo(0,0)')
            await pg.click('#open-subscribe'); await state('abo')
            await pg.fill('#account-email', 'sehr.lange.adresse.zum.testen@beispiel-domain.de')
            await pg.click('.confirm-subscribe'); await state('abo-bestaetigt')
            await pg.click('#account-done')
            await pg.click('#account-login'); await state('login')
            await pg.click('#close-account')
            await pg.select_option('#language', 'en'); await state('englisch')
            if errors:
                print(w, 'JS-Fehler', errors)
            await ctx.close()
        print('SUMME', totals or 'keine Auffaelligkeiten')
        await b.close()
    return 1 if totals else 0

sys.exit(asyncio.run(main()))
