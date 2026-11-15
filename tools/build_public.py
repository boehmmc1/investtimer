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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))
import update_stress as engine  # noqa: E402


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
                "render();\n"
                "/* Live-Wert nachladen; bei Fehler bleibt der eingebettete Stand stehen. */\n"
                "if(location.protocol.startsWith('http'))fetch('/data/stress.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject())"
                ".then(d=>{const live=normaliseResult(d);if(live){result=live;render()}}).catch(()=>{});\n"
                "\n})();\n(() => {\n/* 04 ·", "Live-Abruf")

    for leftover in ("investtimer-snapshot", "evaluateSnapshot", "metricRows", "configRows", "Fear_Greed_Index"):
        if leftover in html:
            raise SystemExit("Rest gefunden: " + leftover)
    Path(target).write_text(html, encoding="utf-8")
    print("ok: Rueckfall-Wert %s, %s Bestandteile, %d Bytes" % (fallback["rounded"], fallback["count"], len(html.encode())))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
