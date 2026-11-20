"""KI-Bereich (#ki): Start (aus/ein), Karten, Fragen fuellen die Eingabe, Gespraech, Folgefragen, Neues Gespraech, Tab-Wechsel,
Fehlermeldungen, "Frag die KI dazu" (vorbefuellt, nicht gesendet), nichts unter Eingabe/Tab-Leiste."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
PRUEF = (Path(__file__).parent / 'pruefen.js').read_text()
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
async def sicht(pg, tag):
    await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(250)
    a = await pg.evaluate(PRUEF, {'bereich': 'oben'})
    await pg.evaluate("window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})"); await pg.wait_for_timeout(900)
    await pg.evaluate("window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})"); await pg.wait_for_timeout(200)
    b = await pg.evaluate(PRUEF, {'bereich': 'unten'})
    pruefe(not a and not b, f'{tag}: nichts abgeschnitten/ueberdeckt {(a + b)[:6]}')
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for w, h in ((320, 568), (390, 844), (430, 932), (1280, 860)):
            for ein in (False, True):
                harness.ZUSTAND.update(chat_status=200, frei={'verbraucht': False, 'ausgelastet': False})
                ctx = await br.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 900, has_touch=w < 900, device_scale_factor=2)
                await harness.supabase_route(ctx)
                pg = await ctx.new_page(); js = []
                pg.on('pageerror', lambda e: js.append(str(e)))
                await pg.goto(url + (harness.LOGIN_HASH if ein else '') ); await pg.wait_for_timeout(1000)
                await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(900)
                tag = f'{w} {"ein" if ein else "aus"}'
                g = await pg.evaluate("[...document.querySelectorAll('.ki-gruppe')].map(x=>x.querySelectorAll('.ki-frage').length)")
                pruefe(g == [3, 3, 3], f'{tag}: drei Gruppen mit je drei Fragen {g}')
                txt = await pg.evaluate("document.querySelector('#ki-ansicht').innerText")
                pruefe('Was bewegt dich am Markt?' in txt and ('Anmelden & KI fragen' in txt) == (not ein), f'{tag}: Ueberschrift, Anmelde-Knopf nur ausgeloggt')
                if ein: pruefe('STAND HEUTE' in txt.upper() and '1 freie Frage pro Tag · Beispielfragen unbegrenzt' in txt and 'Noch' not in txt and 'Keine Anlageberatung' in txt, f'{tag}: Eyebrow mit Wert, Hinweiszeile mit Restfragen')
                for k in ('VIX', 'S&P', 'MOVE', 'Put/Call', '{wert}', '…', 'Frag die KI dazu'):
                    pruefe(k not in txt, f'{tag}: kein "{k}" in der KI-Ansicht')
                if w < 760:
                    k = await pg.evaluate("""()=>{const b=document.querySelector('.ki-gruppen').getBoundingClientRect(),ks=[...document.querySelectorAll('.ki-gruppe')];
                      const inhalt=document.querySelector('.ki-gruppen').clientWidth-parseFloat(getComputedStyle(document.querySelector('.ki-gruppen')).paddingLeft)*2;return ks.map(x=>{const r=x.getBoundingClientRect();return {breite:Math.round(r.width/inhalt*100),halb:x.classList.contains('ki-gruppe-halb'),sichtbar:Math.round(Math.max(0,Math.min(r.right,innerWidth)-Math.max(r.left,0)))}})}""")
                    pruefe(80 <= k[0]['breite'] <= 90 and not k[0]['halb'] and k[1]['halb'] and k[1]['sichtbar'] > 10, f'{tag}: Karte ~85 %, Nachbarkarte ragt leer ins Bild {k[:2]}')
                    pruefe(await pg.evaluate("document.querySelectorAll('.ki-punkt').length===3&&getComputedStyle(document.querySelector('.ki-punkte')).display!=='none'"), f'{tag}: Punkte-Anzeige')
                    await pg.evaluate("document.querySelector('.ki-gruppen').scrollTo({left:document.querySelectorAll('.ki-gruppe')[1].offsetLeft-23})"); await pg.wait_for_timeout(500)
                    k2 = await pg.evaluate("[...document.querySelectorAll('.ki-gruppe')].map(x=>x.classList.contains('ki-gruppe-halb'))")
                    pruefe(k2 == [True, False, True], f'{tag}: nach Wischen zweite Karte ganz, Nachbarn leer {k2}')
                    await pg.evaluate("document.querySelector('.ki-gruppen').scrollTo({left:0})"); await pg.wait_for_timeout(400)
                else:
                    hs = await pg.evaluate("[...document.querySelectorAll('.ki-gruppe')].map(x=>Math.round(x.getBoundingClientRect().height))")
                    pruefe(len(set(hs)) == 1, f'{tag}: drei Karten gleich hoch {hs}')
                await sicht(pg, tag + ' Start')
                if SHOT: await pg.evaluate("window.scrollTo(0,0)"); await pg.screenshot(path=str(SHOT / f'ki_start_{w}_{"ein" if ein else "aus"}.png'))
                if not ein:
                    await pg.click('.ki-frage'); await pg.wait_for_timeout(400)
                    pruefe(await pg.evaluate("!!document.querySelector('dialog[open]')"), f'{tag}: Frage ausgeloggt oeffnet Anmeldung')
                    await ctx.close(); continue
                frage = await pg.evaluate("document.querySelector('.ki-gruppe:not(.ki-gruppe-halb) .ki-frage').dataset.frage")
                await pg.click('.ki-gruppe:not(.ki-gruppe-halb) .ki-frage'); await pg.wait_for_timeout(300)
                pruefe(await pg.input_value('#ki-eingabe') == frage and not [a for a in harness.ZUSTAND['aufrufe'] if a[:2] == ('POST', '/api/chat')], f'{tag}: Klick fuellt die Eingabe, sendet nicht')
                harness.ZUSTAND['aufrufe'].clear()
                await pg.press('#ki-eingabe', 'Enter'); await pg.wait_for_timeout(150)
                pruefe(await pg.evaluate("document.querySelector('.ki-kugel-klein')?.classList.contains('denkt')"), f'{tag}: kleine Kugel denkt')
                await pg.wait_for_selector('.ki-antwort', timeout=8000); await pg.wait_for_timeout(900)
                r = await pg.evaluate("""()=>{const a=document.querySelector('.ki-antwort'),letzt=a.lastElementChild,ab=a.getBoundingClientRect(),lb=letzt.getBoundingClientRect();
                   return {du:document.querySelector('.ki-du').getBoundingClientRect().right>innerWidth*0.6,folge:document.querySelectorAll('.ki-folge .ki-chip').length,
                   belege:document.querySelectorAll('.ki-beleg,.ki-spark,.ki-teil').length,letzt:letzt.className,abstand:Math.round(ab.bottom-lb.bottom),log:document.querySelector('.ki-nachrichten').getAttribute('aria-live')}}""")
                pruefe(r['du'] and r['folge'] == 2 and r['belege'] == 0 and r['letzt'] == 'ki-folge' and 8 <= r['abstand'] <= 24 and r['log'] == 'polite', f'{tag}: Gespraech: Frage rechts, Antwort ohne Belege, endet sauber mit 2 Folgefragen, aria-live {r}')
                ok = await pg.evaluate("""()=>{const a=[...document.querySelectorAll('.ki-antwort')].pop().getBoundingClientRect(),u=document.querySelector('.ki-unten').getBoundingClientRect();return a.top>=0&&a.top<u.top-40}""")
                pruefe(ok, f'{tag}: Auto-Scroll zeigt den Anfang der Antwort oberhalb der Eingabe')
                await pg.evaluate("window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})"); await pg.wait_for_timeout(300)
                ok = await pg.evaluate("""()=>{const a=[...document.querySelectorAll('.ki-antwort')].pop().getBoundingClientRect(),u=document.querySelector('.ki-unten').getBoundingClientRect();return a.bottom<=u.top+1}""")
                pruefe(ok, f'{tag}: ganz unten endet die letzte Antwort oberhalb der Eingabe')
                await sicht(pg, tag + ' Gespraech')
                if SHOT: await pg.screenshot(path=str(SHOT / f'ki_gespraech_{w}.png'))
                await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(500); await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(600)
                pruefe(await pg.evaluate("document.querySelectorAll('.ki-antwort').length") == 1, f'{tag}: Gespraech bleibt beim Tab-Wechsel')
                for status, schl in ((429, 'verbraucht'), (401, 'abgelaufen'), (503, 'ausgeschaltet'), (0, 'Keine Verbindung')):
                    harness.ZUSTAND['chat_status'] = status if status else 200
                    if status == 0: await pg.route('**/api/chat', lambda route: route.abort() if route.request.method == 'POST' else route.continue_())
                    await pg.fill('#ki-eingabe', 'Testfrage'); await pg.press('#ki-eingabe', 'Enter'); await pg.wait_for_timeout(900)
                    t = await pg.evaluate("[...document.querySelectorAll('.ki-fehler')].pop()?.innerText||''")
                    pruefe(schl in t, f'{tag}: Meldung bei {status or "Netzfehler"}: {t[:60]}')
                    if status == 401: await pg.goto('about:blank'); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(900); await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(600)
                    if status == 429: await pg.goto('about:blank'); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(900); await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(600)
                await pg.unroute('**/api/chat'); harness.ZUSTAND['chat_status'] = 200
                await pg.click('[data-ki=neu]'); await pg.wait_for_timeout(400)
                pruefe(await pg.evaluate("!!document.querySelector('.ki-start')&&!document.querySelector('.ki-antwort')"), f'{tag}: Neues Gespraech')
                # KI-Bruecke am Wert: KI-Tab mit Kontext, passende Gruppe hervorgehoben, nichts gesendet oder vorbefuellt
                await pg.evaluate("history.pushState(null,'',location.pathname);dispatchEvent(new PopStateEvent('popstate'))"); await pg.wait_for_timeout(500)
                harness.ZUSTAND['aufrufe'].clear()
                await pg.click('.ki-bruecke-start .ki-bruecke' if w < 760 else '.ki-bruecke-knopf'); await pg.wait_for_timeout(800)
                r = await pg.evaluate("""()=>({hash:location.hash,kontext:document.querySelector('.ki-kontext')?.textContent||'',hervor:document.querySelector('.ki-gruppe-hervor h3')?.textContent||'',
                   erste:document.querySelector('.ki-gruppe-hervor .ki-frage')?.textContent||'',eingabe:document.querySelector('#ki-eingabe')?.value,
                   sicht:(()=>{const g=document.querySelector('.ki-gruppe-hervor');return g&&!g.classList.contains('ki-gruppe-halb')})()})""")
                pruefe(r['hash'] == '#ki' and r['kontext'].startswith('Du kommst von: Marktstress') and r['hervor'].lower().startswith('einordnen') and r['erste'].startswith('Ist ') and r['eingabe'] == '' and r['sicht']
                       and not [a for a in harness.ZUSTAND['aufrufe'] if a[:2] == ('POST', '/api/chat')], f'{tag}: KI-Bruecke oeffnet KI mit Kontext, nichts vorbefuellt/gesendet {r}')
                await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(500); await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(500)
                pruefe(not await pg.evaluate("!!document.querySelector('.ki-kontext')"), f'{tag}: direkt geoeffneter KI-Tab ohne Herkunftszeile')
                await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1200)
                await pg.click('.ereignis-karte .ki-bruecke'); await pg.wait_for_timeout(800)
                r = await pg.evaluate("({kontext:document.querySelector('.ki-kontext')?.textContent||'',erste:document.querySelector('.ki-gruppe-hervor .ki-frage')?.textContent||''})")
                pruefe('phase' in r['kontext'].lower() and r['erste'].startswith('Wie verlief'), f'{tag}: Bruecke aus der Ereigniskarte {r}')
                pruefe(await pg.evaluate("getComputedStyle(document.querySelector('#ki-eingabe')).fontSize") == '16px', f'{tag}: Eingabe 16 px')
                pruefe(not js, f'{tag}: keine JS-Fehler {js}')
                await ctx.close()
        await br.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
