"""Blocke K, A, B (Auftrag 25.11.2026): Reiter Aufbau und Startseiten-Karte (ein-/ausgeloggt, DE/EN), Aufklappen, Erklaerungs-Blatt,
keine Gewichtungen sichtbar; ausgeloggt: schlanke Hinweiszeile auf allen Reitern, Label "MARKTSTRESS AM …", Werte und Datum aus demselben
zeitversetzten Stand (<= heute-30), Verlauf ohne 5J/Alle und hoechstens ein Jahr; Reihenfolge der Karten unter dem Einordnungssatz.
Screenshots nach <ordner>."""
import asyncio, sys, json, re
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import harness
from playwright.async_api import async_playwright
SHOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
fehler = []
def pruefe(bed, text):
    print(('ok   ' if bed else 'FEHL ') + text)
    if not bed: fehler.append(text)
PUB = harness.stress_json()['publicSnapshot']
GRENZE = (date.today() - timedelta(days=30)).isoformat()
RUND = lambda x: int(x + 0.5)

async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for ein in (False, True):
            for w, h in ((320, 568), (375, 812), (390, 844), (1280, 860)):
                for sp in (('de', 'en') if w in (390, 1280) else ('de',)):
                    tag = f'{w} {"ein" if ein else "aus"} {sp}'
                    mobil = w < 760
                    ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=mobil, has_touch=mobil, device_scale_factor=2 if SHOT else 1)
                    await harness.supabase_route(ctx)
                    pg = await ctx.new_page(); js = []
                    pg.on('pageerror', lambda e: js.append(str(e)))
                    pg.on('console', lambda m: js.append(m.text) if m.type == 'error' else None)
                    await pg.goto(url + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1800)
                    if sp == 'en':
                        await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(400)
                    # Reihenfolge unter dem Einordnungssatz
                    folge = await pg.evaluate("""()=>{const as=document.querySelector('.assessment'),o=[];let e=as.nextElementSibling;
                      while(e&&o.length<5){if(e.offsetHeight)o.push(e.id||e.className.split(' ')[0]);e=e.nextElementSibling}return o}""")
                    erwartet = ['aufbau-karte', 'alarm-karte'] + (['ki-bruecke-start'] if mobil else [])
                    pruefe(folge[:len(erwartet)] == erwartet, f'{tag}: Reihenfolge {folge[:4]}')
                    abst = await pg.evaluate("Math.round(document.querySelector('#alarm-karte').getBoundingClientRect().top-document.querySelector('#aufbau-karte').getBoundingClientRect().bottom)")
                    pruefe(abst == 10, f'{tag}: Abstand Aufbau-Karte -> Alarm 10 px ({abst})')
                    k = await pg.evaluate("""()=>{const k=document.querySelector('#aufbau-karte');return {kopf:k.querySelector('.aufbau-label').textContent,details:k.querySelector('.aufbau-details').textContent,
                      zeilen:[...k.querySelectorAll('.aufbau-zeile')].map(z=>[z.querySelector('.aufbau-name').textContent,z.querySelector('.aufbau-wert').textContent,
                        Math.round(z.querySelector('.aufbau-spur').getBoundingClientRect().height),z.querySelector('.aufbau-spur>span').style.width]),
                      stand:k.querySelector('.aufbau-stand')?.textContent||'',href:k.getAttribute('href'),score:document.querySelector('.gauge-stage .score').textContent}}""")
                    if not ein:
                        bl = PUB.get('bloecke') or {}
                        werte = [str(RUND(bl[x])) for x in ('volatility', 'price', 'positioning')] if bl else []
                        pruefe(k['kopf'] == ('DAS STECKTE IN DER %s' if sp == 'de' else 'WHAT MADE UP THE %s') % PUB['rounded'] and [z[1] for z in k['zeilen']] == werte
                               and k['score'] == str(PUB['rounded']) and ('Stand' in k['stand'] or 'As of' in k['stand']), f'{tag}: Karte mit zeitversetzten Werten {k["kopf"]} {[z[1] for z in k["zeilen"]]} = {werte}')
                    else:
                        pruefe(k['kopf'].startswith('DAS STECKT IN DER' if sp == 'de' else 'WHAT MAKES UP THE') and len(k['zeilen']) == 3 and not k['stand'], f'{tag}: Karte eingeloggt {k["kopf"]}')
                    pruefe(all(z[2] == 4 for z in k['zeilen']) and k['href'] == '#aufbau', f'{tag}: Balken 4 px, ganze Karte fuehrt zu #aufbau')
                    # Ausgeloggt: Hinweiszeile, Label, keine Pille
                    hz = await pg.evaluate("""()=>{const z=document.querySelector('.zeitversatz-zeile'),p=z&&z.querySelector('p');if(!z||z.hidden)return null;
                      const r=z.getBoundingClientRect(),lh=parseFloat(getComputedStyle(p).lineHeight)||17;return {text:z.innerText.replace(/\\s+/g,' '),zeilen:Math.round(p.getBoundingClientRect().height/lh),bg:getComputedStyle(z).backgroundColor,
                       links:Math.round(r.left),rechts:Math.round(innerWidth-r.right),label:document.querySelector('.label-am').textContent,pille:getComputedStyle(document.querySelector('.snapshot-label')).visibility}}""")
                    if ein:
                        pruefe(hz is None, f'{tag}: eingeloggt keine Hinweiszeile')
                    else:
                        d = date.fromisoformat(PUB['asOf'])
                        pruefe(hz and ('einen Monat zeitversetzt' in hz['text'] if sp == 'de' else 'one month delayed' in hz['text']) and 'kostenlos' not in hz['text'].lower() and ' free' not in hz['text'].lower()
                               and hz['bg'] == 'rgb(245, 237, 223)' and hz['pille'] == 'hidden' and str(d.year) in hz['label'] and ('AM' in hz['label'] or 'ON' in hz['label'])
                               and (hz['zeilen'] <= 2 or w < 375), f'{tag}: Hinweiszeile "{hz and hz["text"][:60]}" ({hz and hz["zeilen"]} Zeilen), Label "{hz and hz["label"]}"')
                    if SHOT and sp == 'de' and w in (390, 1280): await pg.screenshot(path=str(SHOT / f'start_{"ein" if ein else "aus"}_{w}.png'))
                    # Reiter Aufbau
                    await pg.click('#aufbau-karte'); await pg.wait_for_timeout(700)
                    a = await pg.evaluate("""()=>({hash:location.hash,sicht:!document.querySelector('#aufbau-ansicht').hidden,titel:document.querySelector('#aufbau-titel').textContent,
                      gruppen:[...document.querySelectorAll('.aufbau-gruppe h3')].map(x=>x.textContent),knopf:[...document.querySelectorAll('.aufbau-auf')].map(x=>x.textContent),
                      breite:Math.round(document.querySelector('.aufbau-inhalt').getBoundingClientRect().width),hinweis:!!document.querySelector('.zeitversatz-zeile:not([hidden])'),
                      aktiv:document.querySelector('.it-leiste [aria-current=page],.it-tabs [aria-current=page]')?.dataset.ziel})""")
                    pruefe(a['hash'] == '#aufbau' and a['sicht'] and a['aktiv'] == 'aufbau' and len(a['gruppen']) == 3 and all(re.search(r'\((5|4)\)', x) for x in a['knopf'])
                           and a['breite'] <= 680 and a['hinweis'] == (not ein), f'{tag}: Reiter Aufbau {a["titel"]} {a["knopf"]} Breite {a["breite"]}')
                    await pg.click('[data-gruppe="price"]'); await pg.wait_for_timeout(250)
                    n = await pg.evaluate("document.querySelectorAll('#aufbau-teile-price:not([hidden]) [data-erkl]').length")
                    pruefe(n >= 4, f'{tag}: Aufklappen zeigt die Bestandteile ({n})')
                    if SHOT and sp == 'de' and w in (390, 1280): await pg.screenshot(path=str(SHOT / f'aufbau_{"ein" if ein else "aus"}_{w}.png'), full_page=True)
                    await pg.click('#aufbau-teile-price [data-erkl] >> nth=0'); await pg.wait_for_timeout(400)
                    bl = await pg.evaluate("""()=>{const d=document.querySelector('.aufbau-blatt');return d&&d.open?{h:[...d.querySelectorAll('h3')].length,titel:d.querySelector('h2').textContent,ueber:d.scrollWidth>d.clientWidth+1}:null}""")
                    pruefe(bl and bl['h'] == 3 and not bl['ueber'], f'{tag}: Erklaerungs-Blatt {bl}')
                    if SHOT and sp == 'de' and w == 390: await pg.screenshot(path=str(SHOT / f'aufbau_blatt_{"ein" if ein else "aus"}_{w}.png'))
                    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
                    txt = await pg.evaluate("document.querySelector('#aufbau-ansicht').innerText+' '+document.querySelector('#aufbau-karte').innerText")
                    pruefe(not re.search(r'\d+ ?%|von 14|of 14|Gewicht|weight', txt), f'{tag}: keine Gewichtungen, keine Anzahl Bestandteile')
                    # Verlauf: ausgeloggt hoechstens 1 Jahr
                    await pg.evaluate("location.hash='verlauf'"); await pg.wait_for_timeout(1400)
                    v = await pg.evaluate("""()=>({sp:[...document.querySelectorAll('[data-spanne]')].map(x=>x.dataset.spanne),hinweis:!!document.querySelector('.zeitversatz-zeile:not([hidden])'),
                      wz:document.querySelector('.verlauf-wertzeile .wz-text')?.textContent||''})""")
                    if ein:
                        pruefe(v['sp'] == ['1M', '3M', '1J', '5J', 'A'] and not v['hinweis'], f'{tag}: Verlauf eingeloggt alle Zeitraeume {v["sp"]}')
                    else:
                        pruefe(v['sp'] == ['1M', '3M', '1J'] and v['hinweis'] and v['wz'].startswith('Stand ' if sp == 'de' else 'As of '), f'{tag}: Verlauf ausgeloggt nur bis 1J {v}')
                    await pg.evaluate("location.hash='ki'"); await pg.wait_for_timeout(900)
                    pruefe((await pg.evaluate("!!document.querySelector('.zeitversatz-zeile:not([hidden])')")) == (not ein), f'{tag}: Hinweiszeile im Reiter KI {"nicht " if ein else ""}sichtbar')
                    pruefe(not js, f'{tag}: keine Konsolenfehler {js[:2]}')
                    await ctx.close()
        await b.close()
    # Oeffentliche Daten (Harness = gleicher Code wie die API)
    hist = harness.HIST_BIS(harness.HIST(), PUB['asOf'], (date.fromisoformat(PUB['asOf']) - timedelta(days=365)).isoformat())
    von = (date.fromisoformat(PUB['asOf']) - timedelta(days=365)).isoformat()
    erste = min(r[0][0] for r in (hist['taeglich'], hist['woechentlich'], hist['monatlich']) if r)
    pruefe(PUB['asOf'] <= GRENZE and erste >= von and all(e['start'] >= von and e['spitze']['d'] <= PUB['asOf'] for e in hist['ereignisse']),
           f'oeffentlich: Stand {PUB["asOf"]} <= {GRENZE}, Verlauf ab {erste} (>= {von})')
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
