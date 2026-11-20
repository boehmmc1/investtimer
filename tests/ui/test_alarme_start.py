"""Alarme auf der Startseite (Auftrag 20.11.2026): Karte (ausgeloggt, 0/1/6 Alarme, nur ausgeloeste), Blatt (Vorbelegung, Richtung,
Schwelle, "liegt schon ueber", Richtung voll, Kanaele, Push nicht erlaubt, Bearbeiten, Loeschen), Liste (Gruppen, ausgeloeste
aufklappbar, Grenze), hoechstens zwei Marken am Bogen mit Schild, Schwellen im Verlauf, Grenze 3 je Richtung auch in der API,
Bestandskonto mit mehr als 3, Teilen-Symbol neben der Pille. 320/390/430/1280, DE/EN, keine Konsolenfehler.
Server-Logik ist echt (volafly-api/investtimer_alarme.py mit Wegwerf-Datenbank). Screenshots nach <ordner>."""
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
SECHS = [('ueber', 40, 1, None), ('ueber', 60, 1, None), ('ueber', 75, 1, None), ('unter', 30, 1, None), ('unter', 20, 1, None), ('unter', 35, 0, '2026-11-18')]
KARTE = "()=>{const k=document.querySelector('#alarm-karte button');if(!k)return null;const r=k.getBoundingClientRect();return {h:Math.round(r.height),w:Math.round(r.width),text:k.innerText.replace(/\\n+/g,' | '),aktion:k.dataset.alarm}}"
UEBERLAUF = """()=>{const d=document.querySelector('.alarm-blatt');if(!d||!d.open)return 'zu';const r=d.getBoundingClientRect(),aus=[];
 if(d.scrollWidth>d.clientWidth+1)aus.push('scrollbreite');
 d.querySelectorAll('h2,button,output,p,.mini-bogen,li').forEach(e=>{const b=e.getBoundingClientRect();if(b.width&&(b.left<r.left-1||b.right>r.right+1))aus.push(e.className||e.tagName)});
 return aus}"""

async def seite(b, w, ein=True, sp='de', h=844):
    mobil = w < 760
    ctx = await b.new_context(viewport={'width': w, 'height': h if mobil else 860}, is_mobile=mobil, has_touch=mobil, device_scale_factor=2 if SHOT else 1)
    await harness.supabase_route(ctx)
    pg = await ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.on('console', lambda m: js.append(m.text) if m.type == 'error' else None)
    await pg.goto(harness.URL + (harness.LOGIN_HASH if ein else '')); await pg.wait_for_timeout(1700)
    if sp == 'en':
        await pg.evaluate("()=>{const h=document.querySelector('#header-language');h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(400)
    return ctx, pg, js

async def bild(pg, name):
    if SHOT: await pg.screenshot(path=str(SHOT / name))

async def marken(pg):
    return await pg.evaluate("""()=>{const s=document.querySelector('.gauge-svg'),p=s.querySelector('.gauge-point'),m=[...s.querySelectorAll('.alarm-marke')];
     const vorPunkt=m.map(x=>!!(x.compareDocumentPosition(p)&Node.DOCUMENT_POSITION_FOLLOWING));
     const c=s.getScreenCTM(),mx=c.a*250+c.e,my=c.d*250+c.f;
     const auf=m.map(x=>{const b=x.getBoundingClientRect(),dx=(b.left+b.right)/2-mx,dy=(b.top+b.bottom)/2-my;return Math.abs(Math.hypot(dx,dy)/c.a-200)<3});
     return {n:m.length,knoepfe:document.querySelectorAll('.alarm-marke-knopf').length,vorPunkt,auf,
      groesse:m.map(x=>Math.round(x.getBoundingClientRect().width)),flaeche:[...document.querySelectorAll('.alarm-marke-knopf')].map(x=>Math.round(x.getBoundingClientRect().width))}}""")

async def main():
    srv, url = harness.starten(); harness.URL = url
    harness.ZUSTAND['wert'] = 34
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])

        # --- ausgeloggt: schlanke Zeile, fuehrt zur Anmeldung, danach direkt das Blatt ---
        for w in (390, 1280):
            ctx, pg, js = await seite(b, w, ein=False)
            k = await pg.evaluate(KARTE)
            pruefe(k and k['h'] == 56 and 'Alarm setzen' in k['text'] and k['aktion'] == 'login', f'{w} aus: Zeile "Alarm setzen" 56 px {k}')
            pruefe(await pg.locator('.gauge-svg .alarm-marke').count() == 0, f'{w} aus: keine Marken')
            await bild(pg, f'start_aus_{w}.png')
            await pg.click('#alarm-karte button'); await pg.wait_for_timeout(500)
            pruefe(await pg.evaluate("sessionStorage.getItem('investtimer-nach-login')") == 'alarm' and await pg.evaluate("!!document.querySelector('dialog.access-dialog[open]')"),
                   f'{w} aus: Antippen oeffnet Anmeldung')
            await pg.goto('about:blank'); await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(2200)  # Rueckkehr aus dem E-Mail-Link (neue Seite)
            pruefe(await pg.evaluate("!!document.querySelector('.alarm-blatt')?.open && document.querySelector('#alarm-blatt-titel').textContent==='Alarm einstellen'"),
                   f'{w} aus: nach der Anmeldung oeffnet sich das Alarm-Blatt')
            pruefe(not js, f'{w} aus: keine Konsolenfehler {js}'); await ctx.close()

        # --- eingeloggt, 0 Alarme: Zeile, Blatt, Vorbelegung, Anlegen ---
        for w in (320, 390, 430, 1280):
            harness.alarme_setzen([])
            ctx, pg, js = await seite(b, w)
            k = await pg.evaluate(KARTE)
            pruefe(k and k['h'] == 56 and k['aktion'] == 'neu' and k['text'].strip() == 'Alarm setzen', f'{w} 0 Alarme: Zeile ohne Zusatz {k}')
            lage = await pg.evaluate("""()=>{const a=document.querySelector('.assessment').getBoundingClientRect(),k=document.querySelector('#alarm-karte').getBoundingClientRect(),
              ki=document.querySelector('.ki-bruecke-start'),kr=ki&&ki.getBoundingClientRect(),gr=document.querySelector('.ki-bruecke-gross'),g=gr&&gr.getBoundingClientRect();
              return {unter:Math.round(k.top-a.bottom),vorKi:kr&&kr.height?Math.round(kr.top-k.bottom):null,breite:Math.round(k.width),kiBreite:g&&g.width?Math.round(g.width):kr?Math.round(kr.width):null}}""")
            pruefe(lage['unter'] >= 0 and (lage['vorKi'] is None or 8 <= lage['vorKi'] <= 12) and abs(lage['breite'] - lage['kiBreite']) <= 2,
                   f'{w}: Karte unter dem Einordnungssatz, vor der KI-Karte, gleiche Breite {lage}')
            t = await pg.evaluate("""()=>{const s=document.querySelector('.status-zeile'),k=document.querySelector('.teilen-start .teilen-knopf'),p=document.querySelector('.snapshot-label');
              const kb=k.getBoundingClientRect(),pb=p.getBoundingClientRect();
              return {inStatus:!!s.querySelector('.teilen-knopf'),text:k.innerText.trim(),aria:k.getAttribute('aria-label'),h:Math.round(kb.height),w:Math.round(kb.width),
               mitte:Math.round(Math.abs((kb.top+kb.bottom)/2-(pb.top+pb.bottom)/2)),rechts:kb.left>pb.right,ueberlappt:kb.left<pb.right&&kb.right>pb.left&&kb.top<pb.bottom&&kb.bottom>pb.top,
               farbe:getComputedStyle(k).color,innen:kb.right<=innerWidth}}""")
            pruefe(not t['inStatus'] and t['text'] == '' and t['aria'] == 'Teilen' and t['aria'] and t['h'] >= 44 and t['w'] >= 44 and t['mitte'] <= 2 and t['rechts'] and not t['ueberlappt']
                   and t['farbe'] == 'rgb(110, 123, 116)' and t['innen'], f'{w}: Teilen nur als Symbol rechts auf Hoehe der Pille {t}')
            await bild(pg, f'start_ohne_{w}.png')
            await pg.click('#alarm-karte button'); await pg.wait_for_timeout(500)
            z = await pg.evaluate("()=>({titel:document.querySelector('#alarm-blatt-titel')?.textContent,zahl:document.querySelector('.blatt-zahl')?.textContent,hinweis:document.querySelector('.blatt-hinweis')?.textContent,mb:document.querySelector('.mb-alarm')?.textContent,jetzt:document.querySelector('.mb-jetzt')?.textContent})")
            pruefe(z['titel'] == 'Alarm einstellen' and z['zahl'] == '40' and z['mb'] == 'Alarm über 40' and z['jetzt'] == 'Jetzt 34'
                   and z['hinweis'] == 'Noch 6 Punkte. Du bekommst eine Nachricht, sobald der Marktstress über 40 steigt.', f'{w}: Blatt vorbelegt mit naechster Grenze {z}')
            ue = await pg.evaluate(UEBERLAUF)
            pruefe(ue == [], f'{w}: Blatt ohne Abschneiden {ue}')
            hoehe = await pg.evaluate("Math.round(document.querySelector('.blatt-speichern').getBoundingClientRect().height)")
            pruefe(hoehe == 52, f'{w}: Speichern-Knopf 52 px ({hoehe})')
            if w == 390:
                await bild(pg, 'blatt_normal_390.png')
                await pg.click('[data-richtung="unter"]'); await pg.wait_for_timeout(250)
                z2 = await pg.evaluate("[document.querySelector('.blatt-zahl').textContent,document.querySelector('.blatt-hinweis').textContent]")
                pruefe(z2 == ['20', 'Noch 14 Punkte. Du bekommst eine Nachricht, sobald der Marktstress unter 20 fällt.'], f'Richtungswechsel belegt neu vor {z2}')
                await pg.click('[data-richtung="ueber"]'); await pg.wait_for_timeout(200)
                ring0 = await pg.evaluate("document.querySelector('.mb-ring').getAttribute('cx')")
                for _ in range(10): await pg.click('[data-schritt="-1"]')
                await pg.wait_for_timeout(400)
                z3 = await pg.evaluate("({z:document.querySelector('.blatt-zahl').textContent,h:document.querySelector('.blatt-hinweis').textContent,k:document.querySelector('.blatt-hinweis').className,f:getComputedStyle(document.querySelector('.blatt-hinweis')).color,cx:document.querySelector('.mb-ring').getAttribute('cx')})")
                pruefe(z3['z'] == '30' and z3['h'].startswith('Der Marktstress liegt schon über 30.') and z3['f'] == 'rgb(138, 95, 36)' and z3['cx'] != ring0,
                       f'"liegt schon ueber": Hinweis in #8a5f24, Ring wandert {z3}')
                await bild(pg, 'blatt_schon_390.png')
                # gedrueckt halten = schneller
                await pg.locator('[data-schritt="1"]').dispatch_event('pointerdown'); await pg.wait_for_timeout(1600)
                await pg.locator('[data-schritt="1"]').dispatch_event('pointerup')
                z4 = int(await pg.evaluate("document.querySelector('.blatt-zahl').textContent"))
                pruefe(z4 >= 45, f'gedrueckt halten zaehlt schneller hoch (30 -> {z4})')
                for _ in range(z4 - 40): await pg.click('[data-schritt="-1"]')
                # Kanaele: mindestens einer bleibt an
                await pg.click('[data-kanal="push"]'); await pg.wait_for_timeout(150)
                pruefe(await pg.evaluate("document.querySelector('[data-kanal=push]').getAttribute('aria-pressed')") == 'true', 'letzter Kanal laesst sich nicht abwaehlen')
                await pg.click('[data-kanal="email"]'); await pg.wait_for_timeout(150)
                pruefe('test@investtimer.net' in await pg.inner_text('.alarm-blatt'), 'E-Mail-Adresse wird genannt')
                await pg.click('[data-kanal="email"]'); await pg.wait_for_timeout(150)
                await pg.click('[data-alarm="speichern"]'); await pg.wait_for_timeout(900)
                push = await pg.evaluate("document.querySelector('.blatt-push')?.innerText||''")
                pruefe('Mitteilungen' in push and 'Alarm gespeichert' in push, f'Push nicht erlaubt: freundliches Angebot nach dem Speichern "{push[:80]}"')
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
                k1 = await pg.evaluate(KARTE)
                pruefe(k1 and '1 ALARM' in k1['text'] and 'Nächster: über 40' in k1['text'] and 'Noch 6 Punkte' in k1['text'] and '·' not in k1['text'].split('|')[-2], f'1 Alarm: Karte {k1}')
                m = await marken(pg)
                pruefe(m['n'] == 1 and all(m['auf']) and m['flaeche'] == [44] and 7 <= m['groesse'][0] <= 9, f'1 Alarm: eine Marke auf der Bogenlinie {m}')
            pruefe(not js, f'{w}: keine Konsolenfehler {js}'); await ctx.close()

        # --- 6 Alarme (3+3, einer ausgeloest): Karte, Marken, Schild, Liste, Richtung voll ---
        for w in (320, 390, 1280):
            for sp in (('de', 'en') if w == 390 else ('de',)):
                harness.alarme_setzen(SECHS)
                ctx, pg, js = await seite(b, w, sp=sp)
                await pg.wait_for_timeout(900)
                k = await pg.evaluate(KARTE)
                if sp == 'de':
                    pruefe(k and 76 <= k['h'] <= 96 and '6 ALARME' in k['text'] and 'Nächster: unter 30' in k['text'] and 'Noch 4 Punkte · nach oben: über 40' in k['text'],
                           f'{w}: 6 Alarme Karte {k}')
                else:
                    pruefe(k and 76 <= k['h'] <= 96 and '6 ALERTS' in k['text'] and 'Next: below 30' in k['text'] and '4 points to go · on the way up: above 40' in k['text'], f'{w} EN: Karte {k}')
                m = await marken(pg)
                pruefe(m['n'] == 2 and m['knoepfe'] == 2 and all(m['auf']) and all(7 <= g <= 9 for g in m['groesse']) and all(f >= 44 for f in m['flaeche']),
                       f'{w} {sp}: genau zwei Marken auf der Linie, 10 px mit Rand (Fuellung 8), Flaeche >= 44 px {m}')
                await pg.click('.alarm-marke-knopf >> nth=0'); await pg.wait_for_timeout(300)
                s = await pg.evaluate("""()=>{const s=document.querySelector('.alarm-schild');if(!s)return null;const r=s.getBoundingClientRect(),z=document.querySelector('.gauge-stage .score').getBoundingClientRect();
                  const ueber=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
                  const sv=document.querySelector('.gauge-svg').getBoundingClientRect(),k=sv.width/500,mx=sv.left+250*k,my=sv.top+250*k;
                  const ecken=[[r.left,r.top],[r.right,r.top],[r.left,r.bottom],[r.right,r.bottom]].map(([x,y])=>Math.hypot(x-mx,y-my)/k);
                  return {text:s.textContent,zahl:ueber(r,{left:z.left+z.width*.12,right:z.right-z.width*.12,top:z.top+z.height*.15,bottom:z.bottom-z.height*.1}),innen:r.left>=0&&r.right<=innerWidth,
                   aussen:Math.min(...ecken)>200||Math.max(...ecken)<190,fs:getComputedStyle(s).fontSize}}""")
                erwartet = ('über 40 · noch 6', 'unter 30 · noch 4') if sp == 'de' else ('above 40 · 6 to go', 'below 30 · 4 to go')
                pruefe(s and s['text'] in erwartet and s['aussen'] and not s['zahl'] and s['innen'] and s['fs'] == '12px', f'{w} {sp}: Schild "{s and s["text"]}" ueberdeckt nichts {s}')
                if sp == 'de': await bild(pg, f'start_alarme_schild_{w}.png')
                await pg.click('.alarm-marke-knopf >> nth=0'); await pg.wait_for_timeout(200)
                pruefe(await pg.locator('.alarm-schild').count() == 0, f'{w} {sp}: erneutes Tippen schliesst das Schild')
                await pg.click('.alarm-marke-knopf >> nth=1'); await pg.wait_for_timeout(200); await pg.mouse.click(5, 300); await pg.wait_for_timeout(200)
                pruefe(await pg.locator('.alarm-schild').count() == 0, f'{w} {sp}: Tippen woanders schliesst das Schild')
                await pg.click('#alarm-karte button'); await pg.wait_for_timeout(500)
                l = await pg.evaluate("""()=>({titel:document.querySelector('#alarm-blatt-titel').textContent,unter:document.querySelector('.blatt-unter').textContent,
                  gruppen:[...document.querySelectorAll('.liste-gruppe')].map(g=>g.textContent),
                  zeilen:[...document.querySelectorAll('.liste-gruppe+.liste .liste-zeile')].map(z=>[z.querySelector('.liste-text').textContent,z.querySelector('.liste-rest').textContent,Math.round(z.getBoundingClientRect().height)]),
                  aus:document.querySelector('.liste-aus summary')?.textContent,offen:document.querySelector('.liste-aus')?.open,neu:!!document.querySelector('.blatt-neu'),
                  grenze:document.querySelector('.blatt-klein.mitte')?.textContent})""")
                if sp == 'de':
                    pruefe(l['titel'] == 'Deine Alarme' and l['unter'] == 'Marktstress jetzt 34' and l['gruppen'] == ['WENN ER STEIGT', 'WENN ER FÄLLT']
                           and [z[0] for z in l['zeilen']] == ['über 40', 'über 60', 'über 75', 'unter 30', 'unter 20'] and l['zeilen'][0][1] == 'noch 6'
                           and all(z[2] == 48 for z in l['zeilen']) and l['aus'] == '1 ausgelöst' and not l['offen'] and not l['neu']
                           and l['grenze'] == 'Höchstens 3 Alarme je Richtung.', f'{w}: Liste {l}')
                else:
                    pruefe(l['titel'] == 'Your alerts' and l['gruppen'] == ['IF IT RISES', 'IF IT FALLS'] and l['aus'] == '1 triggered' and l['grenze'] == 'At most 3 alerts per direction.', f'{w} EN: Liste {l}')
                if sp == 'de': await bild(pg, f'liste_zu_{w}.png')
                await pg.click('.liste-aus summary'); await pg.wait_for_timeout(250)
                a = await pg.evaluate("document.querySelector('.liste-zeile.aus').innerText")
                if sp == 'de':
                    pruefe('unter 35 · ausgelöst am 18. Nov.' in a and 'Ausgelöst am 18. Nov. Meldet sich wieder, wenn der Wert über 35 steigt und danach erneut fällt.' in a, f'{w}: ausgeloest aufgeklappt "{a}"')
                    await bild(pg, f'liste_auf_{w}.png')
                else:
                    pruefe('below 35 · triggered Nov 18' in a and 'Triggered on Nov 18. Will notify you again once the score rises above 35 and then falls again.' in a, f'{w} EN: ausgeloest "{a}"')
                ue = await pg.evaluate(UEBERLAUF); pruefe(ue == [], f'{w} {sp}: Liste ohne Abschneiden {ue}')
                pruefe(not js, f'{w} {sp}: keine Konsolenfehler {js}'); await ctx.close()

        # --- Richtung voll (UI + API), Bestandskonto mit 4, Bearbeiten, Loeschen ---
        harness.alarme_setzen([('ueber', 40, 1, None), ('ueber', 60, 1, None), ('ueber', 75, 1, None)])
        ctx, pg, js = await seite(b, 390)
        await pg.click('#alarm-karte button'); await pg.wait_for_timeout(400)
        await pg.click('.blatt-neu'); await pg.wait_for_timeout(400)
        pruefe(await pg.evaluate("document.querySelector('[data-richtung=unter]').getAttribute('aria-pressed')") == 'true', 'Richtung "steigt" voll: Blatt startet mit "faellt unter"')
        await pg.click('[data-richtung="ueber"]'); await pg.wait_for_timeout(200)
        h = await pg.evaluate("document.querySelector('.blatt-hinweis').textContent")
        pruefe(h == 'Du hast schon 3 Alarme für steigenden Marktstress. Ändere oder lösch einen.', f'Richtung voll: Hinweis "{h}"')
        await bild(pg, 'blatt_voll_390.png')
        n0 = len([a for a in harness.ZUSTAND['aufrufe'] if a[0] == 'POST' and a[1] == '/api/alarme'])
        await pg.click('[data-alarm="speichern"]'); await pg.wait_for_timeout(500)
        n1 = len([a for a in harness.ZUSTAND['aufrufe'] if a[0] == 'POST' and a[1] == '/api/alarme'])
        pruefe(n1 == n0 and await pg.evaluate("document.querySelector('.alarm-blatt').open"), 'Richtung voll: Speichern zeigt Hinweis statt zu speichern')
        api = await pg.evaluate("async(t)=>{const r=await fetch('/api/alarme',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+t},body:JSON.stringify({richtung:'ueber',schwelle:90,kanal:'push'})});return [r.status,await r.json()]}", harness.TOKEN)
        pruefe(api[0] == 409 and api[1].get('error') == 'richtung_voll', f'API lehnt 4. Alarm einer Richtung ab {api}')
        # Bearbeiten: Schwelle aendern
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        await pg.click('#alarm-karte button'); await pg.wait_for_timeout(400)
        await pg.click('.liste-zeile >> nth=0'); await pg.wait_for_timeout(400)
        pruefe(await pg.evaluate("document.querySelector('#alarm-blatt-titel').textContent") == 'Alarm bearbeiten' and await pg.evaluate("document.querySelector('.blatt-zahl').textContent") == '40'
               and await pg.locator('[data-alarm="loeschen"]').count() == 1, 'Bearbeiten: Blatt vorbelegt, mit "Alarm loeschen"')
        await bild(pg, 'blatt_bearbeiten_390.png')
        for _ in range(5): await pg.click('[data-schritt="1"]')
        await pg.click('[data-alarm="speichern"]'); await pg.wait_for_timeout(800)
        if await pg.evaluate("!!document.querySelector('.alarm-blatt').open"): await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        pruefe(sorted(a['schwelle'] for a in harness.ALARME.liste(harness.UID)['alarme']) == [45, 60, 75], 'Bearbeiten gespeichert (40 -> 45)')
        # Loeschen mit Rueckfrage
        await pg.click('#alarm-karte button'); await pg.wait_for_timeout(400)
        await pg.click('.liste-zeile >> nth=0'); await pg.wait_for_timeout(400)
        await pg.click('[data-alarm="loeschen"]'); await pg.wait_for_timeout(200)
        pruefe('wirklich löschen' in await pg.inner_text('.blatt-frage') and len(harness.ALARME.liste(harness.UID)['alarme']) == 3, 'Loeschen fragt zurueck')
        await pg.click('[data-alarm="loeschen-ja"]'); await pg.wait_for_timeout(600)
        pruefe(len(harness.ALARME.liste(harness.UID)['alarme']) == 2 and not await pg.evaluate("document.querySelector('.alarm-blatt').open"), 'Loeschen nach Bestaetigung')
        js = [x for x in js if '409' not in x]  # 409 ist der absichtliche API-Test
        pruefe(not js, f'voll/bearbeiten: keine Konsolenfehler {js}'); await ctx.close()

        # Bestandskonto mit 4 ueber-Alarmen: alle gueltig, keine neuen in dieser Richtung
        harness.alarme_setzen([('ueber', x, 1, None) for x in (40, 50, 60, 70)])
        ctx, pg, js = await seite(b, 390)
        k = await pg.evaluate(KARTE); m = await marken(pg)
        pruefe('4 ALARME' in k['text'] and 76 <= k['h'] <= 96 and m['n'] == 1, f'Bestandskonto mit 4: Karte {k}, Marken {m["n"]}')
        await pg.click('#alarm-karte button'); await pg.wait_for_timeout(400)
        pruefe(await pg.locator('.liste-gruppe+.liste .liste-zeile').count() == 4, 'Bestandskonto: alle 4 Alarme in der Liste')
        pruefe(not js, f'Bestandskonto: keine Konsolenfehler {js}'); await ctx.close()

        # Nur ausgeloeste Alarme; Wert genau auf der Schwelle; Marke direkt neben dem Wertpunkt
        harness.alarme_setzen([('ueber', 30, 0, '2026-11-19'), ('unter', 40, 0, '2026-11-17')])
        ctx, pg, js = await seite(b, 390)
        k = await pg.evaluate(KARTE)
        pruefe('Alle Alarme ausgelöst' in k['text'] and 'Melden sich wieder, wenn der Wert zurückkommt' in k['text'] and 76 <= k['h'] <= 96, f'nur ausgeloeste: Karte {k}')
        pruefe((await marken(pg))['n'] == 0, 'nur ausgeloeste: keine Marken')
        await ctx.close()
        harness.alarme_setzen([('ueber', 34, 1, None), ('unter', 33, 1, None)])
        ctx, pg, js = await seite(b, 390)
        k = await pg.evaluate(KARTE); m = await marken(pg)
        pruefe('Nächster: über 34' in k['text'] and 'Genau auf der Schwelle' in k['text'] and m['n'] == 2 and all(m['vorPunkt']), f'Wert auf der Schwelle / Marke neben dem Wertpunkt: Wertpunkt obenauf {k} {m}')
        await bild(pg, 'start_marke_am_punkt_390.png')
        pruefe(not js, f'Schwelle: keine Konsolenfehler {js}'); await ctx.close()

        # --- Verlauf: Linien je bereitem Alarm, Umschalter gemerkt, Hinweis in der Werte-Zeile ---
        for w in (390, 1280):
            harness.alarme_setzen(SECHS)
            ctx, pg, js = await seite(b, w)
            await pg.goto(url + '#verlauf'); await pg.wait_for_timeout(1800)
            await pg.click('[data-spanne="1J"]'); await pg.wait_for_timeout(500)
            v = await pg.evaluate("""()=>{const s=document.querySelector('.verlauf-svg'),l=[...s.querySelectorAll('.verlauf-schwelle')],t=[...s.querySelectorAll('.verlauf-schwelle-text')];
              const r=t.map(x=>x.getBoundingClientRect()),ue=r.some((a,i)=>r.some((b,j)=>i<j&&a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top));
              return {linien:l.length,texte:t.map(x=>x.textContent),hinten:l.every(x=>!!(x.compareDocumentPosition(s.querySelector('.verlauf-linie'))&Node.DOCUMENT_POSITION_FOLLOWING)),ue,
               schalter:document.querySelector('#verlauf-alarme')?.checked}}""")
            pruefe(v['linien'] == 5 and v['texte'] == ['Alarm über 75', 'Alarm über 60', 'Alarm über 40', 'Alarm unter 30', 'Alarm unter 20'] and v['hinten'] and not v['ue'] and v['schalter'],
                   f'{w}: Verlauf mit 5 Schwellen-Linien hinter der Kurve, Beschriftung ohne Ueberlappung {v}')
            await bild(pg, f'verlauf_schwellen_{w}.png')
            # Hinweis "Hier haette dein Alarm ausgeloest": Punkt suchen, an dem die Kurve 40 nach oben ueberquert
            i = await pg.evaluate("()=>{const d=document.querySelector('.verlauf-diagramm');d.focus();return true}")
            treffer = await pg.evaluate("""async()=>{const d=document.querySelector('.verlauf-diagramm');d.dispatchEvent(new KeyboardEvent('keydown',{key:'Home',bubbles:true}));
              for(let i=0;i<400;i++){await new Promise(r=>requestAnimationFrame(r));const z=document.querySelector('.verlauf-wertzeile');if(z.querySelector('.wz-alarm'))return z.innerText;
               d.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))}return null}""")
            pruefe(treffer and 'Hier hätte dein Alarm ausgelöst' in treffer, f'{w}: Werte-Zeile zeigt "Hier haette dein Alarm ausgeloest" ({treffer and treffer.replace(chr(10), " ")})')
            await pg.click('#verlauf-alarme'); await pg.wait_for_timeout(300)
            pruefe(await pg.locator('.verlauf-schwelle').count() == 0, f'{w}: Umschalter blendet Linien aus')
            await pg.reload(); await pg.wait_for_timeout(1800)
            pruefe(await pg.locator('.verlauf-schwelle').count() == 0 and not await pg.evaluate("document.querySelector('#verlauf-alarme').checked"), f'{w}: Zustand gemerkt')
            await pg.click('#verlauf-alarme'); await pg.wait_for_timeout(300)
            pruefe(not js, f'{w} Verlauf: keine Konsolenfehler {js}'); await ctx.close()

        # Konto-Bereich: Zustaende bereit/ausgeloest, oeffnet dieselbe Liste
        harness.alarme_setzen(SECHS)
        ctx, pg, js = await seite(b, 390)
        await pg.goto(url + '#konto'); await pg.wait_for_timeout(1800)
        st = await pg.evaluate("[...document.querySelectorAll('.konto-st')].map(x=>x.textContent)")
        pruefe(sorted(set(st)) == ['ausgelöst', 'bereit'] and st.count('bereit') == 5, f'Konto: Zustaende {st}')
        await pg.click('.konto-alarm >> nth=0'); await pg.wait_for_timeout(500)
        pruefe(await pg.evaluate("document.querySelector('#alarm-blatt-titel')?.textContent") == 'Deine Alarme', 'Konto: Alarm-Eintrag oeffnet die Liste')
        pruefe(not js, f'Konto: keine Konsolenfehler {js}'); await ctx.close()
        await b.close()
    srv.shutdown()
    print('FEHLER: %d' % len(fehler)); sys.exit(1 if fehler else 0)

asyncio.run(main())
