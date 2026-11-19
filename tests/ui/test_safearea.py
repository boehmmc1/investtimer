"""Safe-Area der installierten Web-App (iPhone): Einsaetze per Variable simuliert (47 px oben, 34 px unten, quer 47 px seitlich).
Prueft je Ansicht: nichts Sichtbares beginnt in der Statusleiste, Tab-Leiste und KI-Eingabe liegen ueber dem Home-Balken."""
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
CSS = ':root{--sa-top:%dpx!important;--sa-bottom:%dpx!important;--sa-left:%dpx!important;--sa-right:%dpx!important}'
async def main():
    srv, url = harness.starten()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for (w, h, ins) in ((390, 844, (47, 34, 0, 0)), (844, 390, (0, 21, 47, 47))):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=True, has_touch=True, device_scale_factor=2)
            await harness.supabase_route(ctx)
            pg = await ctx.new_page()
            await pg.goto(url + harness.LOGIN_HASH); await pg.wait_for_timeout(1000)
            await pg.add_style_tag(content=CSS % ins)
            for hsh in ('', 'ki', 'verlauf', 'konto'):
                await pg.evaluate("h=>{location.hash=h;scrollTo(0,0)}", hsh); await pg.wait_for_timeout(900)
                r = await pg.evaluate("""(ins)=>{const [top,bot,l,r]=ins,H=innerHeight,W=innerWidth,out=[];
                  const kopf=document.querySelector('.app-header').getBoundingClientRect();if(kopf.top<top-0.5)out.push('Header oben '+kopf.top);
                  const lei=document.querySelector('.it-leiste');if(lei&&getComputedStyle(lei).display!=='none'){const li=[...lei.querySelectorAll('a')].map(a=>a.getBoundingClientRect());
                    if(li.some(x=>x.bottom>H-bot+0.5))out.push('Tab-Leiste im Home-Balken');if(li[0].left<l-0.5||li[li.length-1].right>W-r+0.5)out.push('Tab-Leiste seitlich');}
                  const ein=document.querySelector('#ki-ansicht:not([hidden]) .ki-form');if(ein){const e=ein.getBoundingClientRect();if(e.bottom>H-bot-(lei&&getComputedStyle(lei).display!=='none'?60:0)+0.5)out.push('KI-Eingabe zu tief '+e.bottom)}
                  for(const el of document.querySelectorAll('h1,h2,p,button,a')){const b=el.getBoundingClientRect();if(!b.width||!b.height||getComputedStyle(el).visibility==='hidden')continue;if(el.closest('[hidden],dialog:not([open])'))continue;
                    if(b.left<l-0.5&&b.right>0)out.push('links im Notch: '+el.tagName+' '+(el.textContent||'').trim().slice(0,20))}
                  return out}""", list(ins))
                pruefe(not r, f'{w}x{h} #{hsh or "start"}: {r}')
                if SHOT: await pg.screenshot(path=str(SHOT / f'sa_{w}_{hsh or "start"}.png'))
            await ctx.close()
        await b.close()
    print('FEHLER:', len(fehler)); return 1 if fehler else 0
sys.exit(asyncio.run(main()))
