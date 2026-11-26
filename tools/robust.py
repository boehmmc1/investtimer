"""Robustheit der Anzeige (Auftrag 25.11.2026, Block E): render(), drawGauge(), updateGauge() und step() brechen nicht mehr ab, wenn
Elemente fehlen (z. B. Bots/Erweiterungen, die den Bogen aus dem DOM nehmen). In diesen Funktionen laufen alle $('…')-Abfragen ueber
$s('…'): fehlt das Element, kommt ein harmloser Platzhalter zurueck (Zuweisungen und Aufrufe laufen ins Leere), und einmalig geht
"Anzeige fehlt im DOM" an /api/fehler. Zusaetzlich: Variablen score/stage in updateGauge/step werden vor Gebrauch geprueft."""
import re

KOPF = r"""<script>/* Block E: sichere Elementabfrage fuer die Anzeige */
(()=>{const leer=new Proxy(function(){},{get:(t,k)=>k===Symbol.toPrimitive?()=>'':k==='length'?0:k==='then'?undefined:leer,set:()=>true,apply:()=>leer});
let gemeldet=false;const warte=[];
window.ITLeer=leer;
window.$s=sel=>{const e=document.querySelector(sel);if(e)return e;
 if(!gemeldet){gemeldet=true;const m=()=>{try{window.ITMeldeFehlt?window.ITMeldeFehlt(sel):warte.push(sel)}catch{}};m()}
 return leer};
window.ITFehltWarte=warte;})();</script>
"""

FUNKTIONEN = ("render", "drawGauge", "updateGauge", "gaugeTicks")


def _koerper(html, start):
    """Index hinter der schliessenden Klammer des Funktionskoerpers ab der ersten '{' nach start (Strings/Template-Literale beachtet)."""
    i = html.index("{", start)
    tiefe, j, n = 0, i, len(html)
    while j < n:
        c = html[j]
        if c in "'\"`":
            q = c; j += 1
            while j < n and html[j] != q:
                j += 2 if html[j] == "\\" else 1
        elif c == "{":
            tiefe += 1
        elif c == "}":
            tiefe -= 1
            if tiefe == 0:
                return i, j + 1
        j += 1
    raise ValueError("Funktionsende nicht gefunden")


def anwenden(html):
    gezaehlt = {}
    for name in FUNKTIONEN:
        for m in list(re.finditer(r"function %s\(" % name, html)):
            pass
        pos = 0
        while True:
            m = re.compile(r"function %s\(" % name).search(html, pos)
            if not m:
                break
            a, b = _koerper(html, m.end())
            teil = html[a:b]
            neu = re.sub(r"(?<![\w$.])\$\((?=['\"`])", "$s(", teil)
            # Existenzpruefungen bleiben echt: if($('x'))$('x')… -> if($('x'))$('x')…
            neu = re.sub(r"if\(\$s\(('[^']*')\)\)\$s\(\1\)", r"if($(\1))$(\1)", neu)
            if name == "updateGauge":
                # score/stage koennen fehlen: dann nur ueberspringen
                neu = neu.replace("{", "{if(!score||!score.isConnected||!stage||!stage.isConnected){$s('.gauge-stage .score');return}", 1)
            html = html[:a] + neu + html[b:]
            gezaehlt[name] = gezaehlt.get(name, 0) + 1
            pos = a + len(neu)
    # step() (Fuell-Animation) ist eine Pfeilfunktion in updateGauge: Abbruch, wenn der Bogen fehlt
    html, n = re.subn(r"const step=now=>\{", "const step=now=>{if(!document.querySelector('.gauge-value')){$s('.gauge-value');gaugeFrame=0;return}", html)
    gezaehlt["step"] = n
    for name in FUNKTIONEN[:3] + ("step",):
        if not gezaehlt.get(name):
            raise SystemExit("Robustheit: Funktion %s nicht gefunden" % name)
    return html.replace("<head>\n", "<head>\n" + KOPF, 1), gezaehlt
