#!/usr/bin/env python3
"""Baut public/index.html aus dem UI-Export (einmaliger Umbau auf Live-Daten).

Aufruf: build_public.py <export.html> <public/index.html>
Aenderungen gegenueber dem Export:
  - Rohwerte, Anker und Rechenkern entfernt (laufen serverseitig)
  - eingebettetes Ergebnis als Rueckfall, Live-Wert aus /data/stress.json
  - Datumsangaben folgen dem Datenstand
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "volafly-api"))
import marktstress as engine  # noqa: E402


LIVE_JS = """/* Live-Wert laden: beim Start und wenn der Tab wieder sichtbar wird (hoechstens alle 5 Minuten). */
let lastLoad=0,lastSeen=JSON.stringify(result);
function loadLive(){
 if(!location.protocol.startsWith('http')||Date.now()-lastLoad<3e5)return;lastLoad=Date.now();
 fetch('/data/stress.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
  const live=normaliseResult(d);if(!live||JSON.stringify(live)===lastSeen||document.querySelector('dialog[open]')){if(live&&JSON.stringify(live)!==lastSeen)lastLoad=0;return}
  const open=$$('#details-panel details').map(e=>e.open),y=window.scrollY;
  result=live;lastSeen=JSON.stringify(live);render();
  $$('#details-panel details').forEach((e,i)=>{e.open=!!open[i]});window.scrollTo(0,y);
 }).catch(()=>{lastLoad=0});
}
loadLive();
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')loadLive()});
window.addEventListener('pageshow',e=>{if(e.persisted)loadLive()});
"""

MOBILE_CSS = """
/* 05 · Mobil-Nachschaerfung (investtimer.net): Tippflaechen, Lesbarkeit, Querformat */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
button,summary,select,label{touch-action:manipulation;-webkit-tap-highlight-color:transparent}
.close-button{width:44px;height:44px;margin:-4px -10px -4px 0}
.clarity-page .details-toggle,.delete-alert,.account-alternative,.account-login,.language-label select{min-height:44px}
.channels label{min-height:44px;padding-right:8px}
@media(pointer:coarse){input:not([type=range]):not([type=radio]):not([type=checkbox]),select,textarea{font-size:16px!important}}
@media(max-width:760px){.scale-ends,.visual-line .scale-ends,.app-footer,.clarity-page .app-footer,.component-count,.delete-alert{font-size:11px}}
@media(max-height:500px) and (orientation:landscape){
.clarity-page .app-header{height:58px}
.clarity-page .first-look{min-height:0;padding:0 0 14px}
.first-look h1{margin-bottom:0}
.gauge-stage{width:236px;height:142px;max-width:100%}
.gauge-stage .score{font-size:104px;letter-spacing:-6px;padding-right:6px}
.clarity-page .details-toggle{margin-top:6px}
.modal,.explanation-modal,.account-dialog{max-height:calc(100dvh - 12px)}
}
"""

HEAD_META = """<meta name="application-name" content="InvestTimer">
<meta name="apple-mobile-web-app-title" content="InvestTimer">
<link rel="canonical" href="https://investtimer.net/">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website"><meta property="og:site_name" content="InvestTimer"><meta property="og:locale" content="de_DE">
<meta property="og:url" content="https://investtimer.net/">
<meta property="og:title" content="InvestTimer — Marktstress auf einen Blick">
<meta property="og:description" content="Ein klarer Wert von 0 bis 100. Details auf Wunsch.">
<meta property="og:image" content="https://investtimer.net/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">"""


def once(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit("Erwartete genau eine Stelle fuer: %s (gefunden %d)" % (label, text.count(old)))
    return text.replace(old, new)


def sub_once(text, pattern, new, label):
    result, n = re.subn(pattern, lambda _m: new, text, flags=re.S)
    if n != 1:
        raise SystemExit("Erwartete genau eine Stelle fuer: %s (gefunden %d)" % (label, n))
    return result


def main(source, target):
    html = Path(source).read_text(encoding="utf-8")

    # Ergebnis des gespeicherten Datenstands als Rueckfall berechnen
    snapshot = json.loads(re.search(
        r'<script type="application/json" id="investtimer-snapshot">(.*?)</script>', html, re.S).group(1))
    result = engine.calculate(engine.metrics_from_rows(snapshot["metricRows"]),
                              engine.config_from_rows(snapshot["configRows"]))
    fallback = {"model": "investtimer-us-market-stress", "asOf": snapshot["asOf"],
                "rounded": result["rounded"], "count": result["count"], "total": result["total"],
                "rows": result["rows"], "blocks": result["blocks"]}

    html = sub_once(html, r"<!--\nINVESTTIMER · COMPLETE SINGLE-FILE UI EXPORT.*?-->",
                    "<!-- InvestTimer · investtimer.net · Quelle: UI-Export v1.0 (Signalbogen) -->", "Kopfkommentar")
    html = once(html, " Clarity mit dem Volafly-Modell aus 14 Komponenten und gespeichertem Datenstand.",
                " 14 Bestandteile, ein Wert.", "Beschreibung")
    html = once(html, "connect-src 'none'", "connect-src 'self'", "CSP")
    html = once(html, '"offline": true', '"offline": false', "Manifest offline")
    html = once(html, '"externalDependencies": []', '"externalDependencies": ["/data/stress.json"]', "Manifest deps")
    html = once(html, '"entryFile": "InvestTimer_UI_Signalbogen_v1.0.html"', '"entryFile": "index.html"', "Manifest Datei")

    html = sub_once(
        html,
        r'<!-- 03 · Saved, replaceable data snapshot -->\n<script type="application/json" id="investtimer-snapshot">.*?</script>',
        '<!-- 03 · Rueckfall-Ergebnis, falls /data/stress.json nicht erreichbar ist -->\n'
        '<script type="application/json" id="investtimer-result">\n%s\n</script>' % json.dumps(fallback, indent=1),
        "Snapshot-Block")

    html = sub_once(html, r"/\* INVESTTIMER EXPORT v1\.0 · no imports, no build step, no network calls\. \*/",
                    "/* InvestTimer · kein Build-Schritt. Live-Wert kommt aus /data/stress.json. */", "Skriptkommentar")
    html = sub_once(
        html, r"const evaluateSnapshot = \(\(\) => \{.*?return evaluateSnapshot;\n\}\)\(\);\n",
        """/* 01 · Ergebnis pruefen (Berechnung laeuft serverseitig) */
function normaliseResult(d){
  if(!d||typeof d!=='object'||!Array.isArray(d.rows)||!Array.isArray(d.blocks))return null;
  const rounded=d.rounded===null?null:Number(d.rounded);
  if(rounded!==null&&!(Number.isInteger(rounded)&&rounded>=0&&rounded<=100))return null;
  const part=r=>r&&typeof r.name==='string'&&Number.isFinite(r.effectiveWeight);
  if(!d.rows.every(part)||!d.blocks.every(part)||!Number.isInteger(d.count))return null;
  return {rounded,count:d.count,rows:d.rows,blocks:d.blocks,asOf:/^\\d{4}-\\d{2}-\\d{2}$/.test(d.asOf)?d.asOf:null};
}
""", "Rechenkern")
    html = sub_once(html, r"// Plain-language summaries grounded in the user's Drive knowledge base\.\n// Source mapping and editorial choices are recorded in docs/plain-language-ui\.md\.\n",
                    "", "Erklaerungs-Kommentar")

    # Datumsangaben dynamisch
    html = once(html, "databody:'Diese Ansicht verwendet den gespeicherten Datenstand vom 15. November 2026. Eine laufende Aktualisierung und ein historischer Verlauf sind noch nicht verbunden.'",
                "databody:'Datenstand: {datelong}. Der Wert wird regelmäßig aktualisiert. Ein historischer Verlauf ist noch nicht verbunden.'", "databody de")
    html = once(html, "databody:'This view uses the saved data snapshot from 15 November 2026. Continuous updates and a historical chart are not connected yet.'",
                "databody:'Data as of {datelong}. The score is updated regularly. A historical chart is not connected yet.'", "databody en")
    html = once(html, "timestamp:'US-Aktienmarkt · Datenstand 15. Nov. 2026'", "timestamp:'US-Aktienmarkt · Datenstand {date}'", "timestamp de")
    html = once(html, "timestamp:'US stock market · Data as of 15 Nov 2026'", "timestamp:'US stock market · Data as of {date}'", "timestamp en")
    html = once(html, "const t=k=>copy[state.lang][k];\nconst number=",
                "const dateLabel=month=>{if(!result?.asOf)return '—';const [y,m,d]=result.asOf.split('-').map(Number);"
                "return new Date(Date.UTC(y,m-1,d)).toLocaleDateString(state.lang==='de'?'de-DE':'en-GB',{day:'numeric',month,year:'numeric',timeZone:'UTC'})};\n"
                "const t=k=>{const v=copy[state.lang][k];return typeof v==='string'?v.replace('{datelong}',()=>dateLabel('long')).replace('{date}',()=>dateLabel('short')):v};\n"
                "const number=", "t()")
    html = once(html, "try{result=evaluateSnapshot(JSON.parse(document.getElementById('investtimer-snapshot').textContent))}catch{result=null}",
                "try{result=normaliseResult(JSON.parse(document.getElementById('investtimer-result').textContent))}catch{result=null}", "Ergebnis laden")
    html = once(html, "render();\n\n})();\n(() => {\n/* 04 ·",
                "render();\n" + LIVE_JS + "\n})();\n(() => {\n/* 04 ·", "Live-Abruf")
    html = once(html, "</style>", MOBILE_CSS + "</style>", "Mobil-CSS")
    html = once(html, "img-src data:;", "img-src 'self' data:;", "CSP Bilder")
    html = once(html, '<meta name="application-name" content="InvestTimer">', HEAD_META, "Kopf-Meta")

    for leftover in ("investtimer-snapshot", "evaluateSnapshot", "metricRows", "configRows", "Fear_Greed_Index"):
        if leftover in html:
            raise SystemExit("Rest gefunden: " + leftover)
    Path(target).write_text(html, encoding="utf-8")
    print("ok: Rueckfall-Wert %s, %s Bestandteile, %d Bytes" % (fallback["rounded"], fallback["count"], len(html.encode())))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
