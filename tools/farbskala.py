"""Fuenf Stufen mit ruhiger, durchgehender Farbskala (Auftrag 19.11.2026, Block 4). Laeuft im Build nach startseite.py.

Stufen: ruhig 0-19, moderat 20-39, erhoeht 40-59, hoch 60-79, Panik 80-100 (gleich breite Bereiche; die Testwerte
15/30/50/70/90 liegen je mittig). Farben: Grafik (Bogen, Punkte, Balken) in der Stufenfarbe, Text in einer
abgedunkelten Fassung mit mindestens 4,5:1 auf dem Seitenhintergrund (WCAG AA). 'hoch' und 'Panik' gegenueber den
Richtwerten etwas dunkler, damit sie bei Deuteranopie unterscheidbar bleiben (Pruefung im Bericht).
Die grosse Zahl bleibt dunkel. Der Bogen faerbt sich beim Fuellen von 'ruhig' in die Zielfarbe.
"""
import re

FARBEN = ["#2E6B57", "#6F7F45", "#A0722F", "#A24524", "#8E2A27"]
TEXT = ["#2E6B57", "#687741", "#93692B", "#A24524", "#8E2A27"]
GRENZEN = [20, 40, 60, 80]

STUFE_JS = ("window.ITStufe=(()=>{const F=%s,T=%s,G=%s;"
            "const stufe=w=>w==null||!Number.isFinite(+w)?null:G.filter(g=>+w>=g).length;"
            "const hex=c=>[1,3,5].map(i=>parseInt(c.slice(i,i+2),16)),zu=a=>'#'+a.map(v=>Math.round(v).toString(16).padStart(2,'0')).join('');"
            "return {stufe,farbe:w=>{const s=stufe(w);return s==null?'#6e7b74':F[s]},text:w=>{const s=stufe(w);return s==null?'#5f6c66':T[s]},"
            "mische:(a,b,k)=>{const x=hex(a),y=hex(b);return zu(x.map((v,i)=>v+(y[i]-v)*Math.max(0,Math.min(1,k))))},ruhig:F[0]}})();\n"
            % (FARBEN, TEXT, GRENZEN))


def _once(html, alt, neu, name):
    n = html.count(alt)
    if n != 1:
        raise SystemExit("farbskala: %s erwartet 1, gefunden %d" % (name, n))
    return html.replace(alt, neu)


def anwenden(html):
    html = _once(html, "function level(value){return value<25?0:value<50?1:value<75?2:3}",
                 STUFE_JS + "function level(value){return ITStufe.stufe(value)}", "level()")
    html = _once(html, "status:['Ruhig','Moderat','Erhöht','Hoch']", "status:['Ruhig','Moderat','Erhöht','Hoch','Panik']", "Stufen de")
    html = _once(html, "status:['Calm','Moderate','Elevated','High']", "status:['Calm','Moderate','Elevated','High','Panic']", "Stufen en")
    # Einordnungssaetze: fuenfter Satz fuer Panik
    m = list(re.finditer(r"summary:\[('(?:[^'\\]|\\.)*',?){4}\]", html))
    if len(m) != 2:
        raise SystemExit("farbskala: summary erwartet 2, gefunden %d" % len(m))
    for treffer, satz in reversed(list(zip(m, ("Am Markt herrscht Panik.", "The market is in panic.")))):
        alt = treffer.group(0)
        html = html[:treffer.start()] + alt[:-1] + ",'" + satz + "']" + html[treffer.end():]
    html = _once(html, "document.documentElement.style.setProperty('--stress',valid?['#3e7c63','#778653','#9b6f32','#ad5e4c'][level(result.rounded)]:'#6e7b74');",
                 "document.documentElement.style.setProperty('--stress',ITStufe.farbe(valid?result.rounded:null));"
                 "document.documentElement.style.setProperty('--stufe-text',ITStufe.text(valid?result.rounded:null));"
                 "document.documentElement.dataset.stufe=valid?String(level(result.rounded)):'';", "Stufenfarbe")
    # Bogen: Farbe beim Fuellen von 'ruhig' zur Zielfarbe; Stufenmarken an den Grenzen
    html = _once(html, " $('.gauge-value').style.strokeDasharray=`${p} 100`;",
                 " $('.gauge-value').style.strokeDasharray=`${p} 100`;\n"
                 " {const ziel=gaugeTarget??p,f=ziel>0?ITStufe.mische(ITStufe.ruhig,ITStufe.farbe(ziel),p/ziel):ITStufe.farbe(ziel);"
                 "$('.gauge-value').style.stroke=f;$('.gauge-point').style.fill=f}", "Bogenfarbe")
    html = _once(html, " [25,50,75].forEach(t=>{const a=(180+t*1.8)*Math.PI/180", " [20,40,60,80].forEach(t=>{const a=(180+t*1.8)*Math.PI/180", "Stufenmarken")
    return html
