#!/usr/bin/env python3
"""Baut die Seite aus dem UI-Export v1.2 (oeffentliche Ansicht + Ansicht nach Login).

Aufruf: build_v12.py <export_v1.2.html> <zielordner> [--vorschau]

Der Export bestimmt Aufbau, Texte und Gestaltung. Ergaenzt wird nur, was ihn
an den Betrieb anschliesst:
  - Rohwerte, Anker und Rechenkern entfernt (laufen in der Volafly-API)
  - zwei Staende aus /data/stress.json: oeffentlich (zeitversetzt) und aktuell
  - KI-Dialog spricht mit /api/chat statt Beispielantworten zu zeigen
  - Film als eigene Datei statt 3,7 MB im HTML
  - "Weitere Fragen" im KI-Dialog aus volafly-api/investtimer_fragen.json

--vorschau: Seite bekommt noindex. Der Ansichtswechsel "Oeffentlich / Nach Login"
bleibt in jedem Fall, bis es eine echte Anmeldung gibt.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "volafly-api"))
sys.path.insert(0, str(ROOT / "tools"))
import marktstress as engine  # noqa: E402
from build_public import MOBILE_CSS, once, sub_once  # noqa: E402

NORMALISE_JS = """/* 01 · Ergebnis pruefen (Berechnung laeuft serverseitig) */
function normaliseResult(d){
  if(!d||typeof d!=='object'||!Array.isArray(d.rows)||!Array.isArray(d.blocks))return null;
  const rounded=d.rounded===null?null:Number(d.rounded);
  if(rounded!==null&&!(Number.isInteger(rounded)&&rounded>=0&&rounded<=100))return null;
  const part=r=>r&&typeof r.name==='string'&&Number.isFinite(r.effectiveWeight);
  if(!d.rows.every(part)||!d.blocks.every(part)||!Number.isInteger(d.count))return null;
  return {rounded,count:d.count,rows:d.rows,blocks:d.blocks,asOf:/^\\d{4}-\\d{2}-\\d{2}$/.test(d.asOf)?d.asOf:null};
}
"""

LIVE_JS = """/* Zwei Staende: oeffentlich (zeitversetzt) und aktuell (nach Anmeldung).
   Solange es keine echte Anmeldung gibt, ist das eine Darstellung, keine Zugriffssperre. */
const IT=window.InvestTimer={live:null,pub:result,member:false,chat:null,
 get view(){return this.member&&this.live?this.live:this.pub},
 setMember(v){this.member=!!v;apply()}};
function apply(){
 const open=$$('#details-panel details').map(e=>e.open),y=window.scrollY;
 result=IT.view;render();
 $$('#details-panel details').forEach((e,i)=>{e.open=!!open[i]});window.scrollTo(0,y);
 document.dispatchEvent(new Event('investtimer:update'));
}
let lastLoad=0,lastSeen='';
function loadLive(){
 if(!location.protocol.startsWith('http')||Date.now()-lastLoad<3e5)return;lastLoad=Date.now();
 fetch('/data/stress.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
  const live=normaliseResult(d),pub=normaliseResult(d.publicSnapshot),seen=JSON.stringify([live,pub]);
  if(!live||seen===lastSeen)return;
  if(document.querySelector('dialog[open]')){lastLoad=0;return}
  IT.live=live;if(pub)IT.pub=pub;lastSeen=seen;apply();
 }).catch(()=>{lastLoad=0});
}
loadLive();
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')loadLive()});
window.addEventListener('pageshow',e=>{if(e.persisted)loadLive()});
if(location.protocol.startsWith('http'))fetch('/api/chat',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{IT.chat=!!(d&&d.ok)}).catch(()=>{IT.chat=false});
"""

CHAT_JS = """const FRAGEN=__FRAGEN__;
function md(text){
 const i=Math.max(text.lastIndexOf('— Basierend auf:'),text.lastIndexOf('— Wissensbasis:'));
 const body=i>0?text.slice(0,i).replace(/\\s+$/,''):text,bold=l=>esc(l).replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>');
 return body.split(/\\n\\s*\\n/).map(block=>{const lines=block.split('\\n').filter(l=>l.trim());if(!lines.length)return '';
  return lines.map(l=>l.startsWith('## ')?'<p class="chat-heading">'+esc(l.slice(3))+'</p>':l.startsWith('- ')?'<p class="chat-point">• '+bold(l.slice(2))+'</p>':'<p>'+bold(l)+'</p>').join('')}).join('');
}
function turnMarkup(turn){return '<div class="chat-bubble chat-question">'+esc(turn.text)+'</div><div class="chat-bubble chat-answer">'+(turn.answer===null?'<span class="chat-wait"><i></i>'+t('thinking')+'</span>':md(turn.answer))+'</div>'}
function moreMarkup(){
 if(lang()!=='de'||busy||!turns.length)return '';
 const asked=new Set(turns.map(x=>x.text)),list=FRAGEN[tab].fragen.filter(q=>!asked.has(q)).slice(0,3);
 return '<div class="chat-more"><span class="sample-label">'+t('more')+'</span><div class="chat-more-tabs" role="tablist">'+FRAGEN.map((k,i)=>'<button type="button" role="tab" data-tab="'+i+'" aria-selected="'+(i===tab)+'">'+esc(k.kurz)+'</button>').join('')+'</div><div class="assistant-chips">'+list.map(q=>'<button type="button" data-more="'+esc(q)+'">'+esc(q)+' '+arrow+'</button>').join('')+'</div></div>';
}
function renderChat(scroll){
 const typed=$('#assistant-chat-input')?.value||'',top=$('.assistant-messages')?.scrollTop||0;
 chat.innerHTML='<div class="assistant-shell"><header class="assistant-top"><div class="modal-top"><span class="eyebrow">'+t('assistantLabel')+'</span><button id="close-assistant" class="close-button" type="button" aria-label="'+t('back')+'">'+(matchMedia('(max-width:760px)').matches?'←':'×')+'</button></div><h2 id="chat-title" tabindex="-1">'+t('chatTitle')+'</h2><p>'+score()+' / 100 · '+t('stand')+' '+date()+'</p></header><div class="assistant-messages" aria-live="polite">'+turns.map(turnMarkup).join('')+moreMarkup()+'</div><footer class="assistant-bottom"><form class="assistant-composer" id="assistant-chat-form"><input id="assistant-chat-input" aria-label="'+t('placeholder')+'" placeholder="'+t('placeholder')+'" maxlength="300" autocomplete="off" enterkeyhint="send" required><button type="submit" aria-label="'+t('send')+'">↑</button></form><p class="assistant-note">'+t('aiNote')+'</p></footer></div>';
 $('#assistant-chat-input').value=typed;
 const box=$('.assistant-messages');
 if(scroll){const last=box.querySelectorAll('.chat-question');const q=last[last.length-1];box.scrollTop=q?Math.max(0,q.offsetTop-box.offsetTop-12):box.scrollHeight}else box.scrollTop=top;
}
async function ask(text){
 text=String(text||'').trim().slice(0,300);if(busy||!text)return;
 const verlauf=turns.filter(x=>x.answer!==null).slice(-3).flatMap(x=>[{role:'user',content:x.text},{role:'assistant',content:x.answer}]);
 const turn={text,answer:null};turns.push(turn);busy=true;renderChat(true);
 let answer='';
 try{
  const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frage:text,verlauf})});
  if(res.status===429)answer=t('limit');else if(!res.ok)throw new Error('HTTP '+res.status);else answer=String((await res.json()).antwort||'');
 }catch{answer=t(IT.chat===false?'unavailable':'offline')}
 turn.answer=answer||t('offline');busy=false;if(chat.open)renderChat(true);
}
function openChat(text,button){
 if(!member){openAccess(button);return}
 opener=button;
 if(!chat.open){renderChat(false);chat.showModal();document.body.classList.add('assistant-open')}
 ask(text);$('#chat-title')?.focus({preventScroll:true});
}
function closeChat(){chat.close();document.body.classList.remove('assistant-open');opener?.focus({preventScroll:true});}
"""

SUBMIT_JS = ("document.addEventListener('submit',e=>{if(!['assistant-entry-form','assistant-chat-form'].includes(e.target.id))return;"
             "e.preventDefault();const input=e.target.querySelector('input');const value=input.value.trim();if(!value)return;input.value='';"
             "if(e.target.id==='assistant-entry-form')openChat(value,e.target.querySelector('button'));else ask(value)});\n")

V12_CSS = """
/* Ergaenzungen fuer den Betrieb: Warten, Antwort-Absaetze, weitere Fragen */
.chat-wait{display:flex;gap:9px;align-items:center;font-size:12px;color:var(--sub)}
.chat-wait i{width:12px;height:12px;border:1.5px solid #bfd3c8;border-top-color:var(--accent);border-radius:50%;animation:chat-spin .8s linear infinite}
@keyframes chat-spin{to{transform:rotate(360deg)}}
.chat-answer .chat-heading{font-weight:600}.chat-answer .chat-point{padding-left:14px;margin-bottom:5px}
.chat-more{flex:none;border-top:1px solid var(--line);padding-top:16px}
.chat-more .sample-label{display:block;color:var(--accent);font-size:10px;letter-spacing:1.3px;margin-bottom:10px}
.chat-more-tabs{display:flex;gap:6px;margin-bottom:10px}
.chat-more-tabs button{font-size:11px;padding:0 13px;min-height:40px;border:1px solid #d7e1d4;border-radius:20px;color:var(--sub)}
.chat-more-tabs button[aria-selected=true]{background:#e5eee4;border-color:#96b5a6;color:var(--text)}
.chat-more .assistant-chips{margin-bottom:0}
.assistant-composer button{height:44px;width:44px}.assistant-composer input{min-height:44px}.market-film-transcript summary{min-height:44px;box-sizing:border-box;padding:15px 0 8px}
.assistant-entry .assistant-note,.assistant-bottom .assistant-note,.member-snapshot-note,.public-access-note,.review-note,.market-film-draft,.snapshot-label{font-size:11px}
.review-switch button{min-height:40px}.header-language{min-width:44px}
@media(prefers-reduced-motion:reduce){.chat-wait i{animation:none}}
"""

KEYS_DE = ("current:'Aktueller Stand',sourceLive:'US-Aktienmarkt · Datenstand ',"
           "aiNote:'Antworten erzeugt eine KI und können Fehler enthalten · Keine Anlageberatung',"
           "thinking:'InvestTimer liest die Daten …',more:'WEITERE FRAGEN',"
           "limit:'Für heute ist das Fragenkontingent erreicht — morgen geht es weiter.',"
           "offline:'Verbindung fehlgeschlagen — bitte in einem Moment erneut versuchen.',"
           "unavailable:'Die KI ist gerade nicht erreichbar.',")
KEYS_EN = ("current:'Latest data',sourceLive:'US stock market · Data as of ',"
           "aiNote:'Answers are generated by AI and may contain errors · Not investment advice',"
           "thinking:'InvestTimer is reading the data …',more:'MORE QUESTIONS',"
           "limit:'Today’s question limit has been reached — please come back tomorrow.',"
           "offline:'Connection failed — please try again in a moment.',"
           "unavailable:'The AI is currently unavailable.',")


def head_meta(preview):
    lines = ['<meta name="application-name" content="InvestTimer">',
             '<meta name="apple-mobile-web-app-title" content="InvestTimer">',
             '<link rel="apple-touch-icon" href="/apple-touch-icon.png">']
    if preview:
        lines.append('<meta name="robots" content="noindex,nofollow">')
    else:
        lines += ['<link rel="canonical" href="https://investtimer.net/">',
                  '<meta property="og:type" content="website"><meta property="og:site_name" content="InvestTimer"><meta property="og:locale" content="de_DE">',
                  '<meta property="og:url" content="https://investtimer.net/">',
                  '<meta property="og:title" content="InvestTimer — Marktstress auf einen Blick">',
                  '<meta property="og:description" content="Ein klarer Wert von 0 bis 100. Details auf Wunsch.">',
                  '<meta property="og:image" content="https://investtimer.net/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
                  '<meta name="twitter:card" content="summary_large_image">']
    return "\n".join(lines)


def main(source, target_dir, preview):
    html = Path(source).read_text(encoding="utf-8")
    target = Path(target_dir)
    (target / "film").mkdir(parents=True, exist_ok=True)

    # Ergebnis des gespeicherten Stands (oeffentlicher Rueckfall mit echtem Datum)
    snapshot = json.loads(re.search(
        r'<script type="application/json" id="investtimer-snapshot">(.*?)</script>', html, re.S).group(1))
    result = engine.calculate(engine.metrics_from_rows(snapshot["metricRows"]),
                              engine.config_from_rows(snapshot["configRows"]))
    fallback = {"model": "investtimer-us-market-stress", "asOf": snapshot["asOf"],
                "rounded": result["rounded"], "count": result["count"], "total": result["total"],
                "rows": result["rows"], "blocks": result["blocks"]}
    (ROOT / "server" / "seed_history.json").write_text(
        json.dumps({fallback["asOf"]: fallback}, indent=1) + "\n", encoding="utf-8")

    # Film als Dateien
    film = json.loads(re.search(r'<script type="application/json" id="investtimer-film-config">(.*?)</script>', html, re.S).group(1))
    (target / "film" / "investtimer-49s.mp4").write_bytes(base64.b64decode(film["src"].split(",", 1)[1]))
    (target / "film" / "poster.jpg").write_bytes(base64.b64decode(film["poster"].split(",", 1)[1]))
    html = sub_once(html, r'<script type="application/json" id="investtimer-film-config">.*?</script>',
                    '<script type="application/json" id="investtimer-film-config">'
                    '{"src":"film/investtimer-49s.mp4","poster":"film/poster.jpg"}</script>', "Film-Daten")

    # Kopf
    html = sub_once(html, r"<!--\nINVESTTIMER · COMPLETE SINGLE-FILE UI EXPORT.*?-->",
                    "<!-- InvestTimer · investtimer.net · Quelle: UI-Export v1.2 (Signalbogen) -->", "Kopfkommentar")
    html = once(html, " Clarity mit dem Volafly-Modell aus 14 Komponenten und gespeichertem Datenstand.",
                " 14 Bestandteile, ein Wert.", "Beschreibung")
    html = once(html, "connect-src 'none'", "connect-src 'self'", "CSP Abrufe")
    html = once(html, "img-src data:;", "img-src 'self' data:;", "CSP Bilder")
    html = once(html, "media-src data:;", "media-src 'self';", "CSP Film")
    html = once(html, '<meta name="application-name" content="InvestTimer">', head_meta(preview), "Kopf-Meta")
    html = sub_once(html, r'(?<=<script type="application/json" id="investtimer-export-manifest">).*?(?=</script>)',
                    "\n" + json.dumps({"artifact": "InvestTimer UI", "exportVersion": "1.2", "languages": ["de", "en"],
                                       "data": "/data/stress.json", "chat": "/api/chat"}, indent=1) + "\n", "Manifest")

    # Daten: Rohwerte und Rechenkern raus, Ergebnis rein
    html = sub_once(
        html,
        r'<!-- 03 · Saved, replaceable data snapshot -->\n<script type="application/json" id="investtimer-snapshot">.*?</script>',
        '<!-- 03 · Oeffentlicher Stand als Rueckfall, falls /data/stress.json nicht erreichbar ist -->\n'
        '<script type="application/json" id="investtimer-result">\n%s\n</script>' % json.dumps(fallback, indent=1),
        "Snapshot-Block")
    html = sub_once(html, r"/\* INVESTTIMER EXPORT v1\.0 · no imports, no build step, no network calls\. \*/",
                    "/* InvestTimer · kein Build-Schritt. Werte kommen aus /data/stress.json. */", "Skriptkommentar")
    html = sub_once(html, r"const evaluateSnapshot = \(\(\) => \{.*?return evaluateSnapshot;\n\}\)\(\);\n", NORMALISE_JS, "Rechenkern")
    html = sub_once(html, r"// Plain-language summaries grounded in the user's Drive knowledge base\.\n// Source mapping and editorial choices are recorded in docs/plain-language-ui\.md\.\n",
                    "", "Erklaerungs-Kommentar")

    # Datumsangaben der Hauptansicht
    html = once(html, "databody:'Diese Ansicht verwendet den gespeicherten Datenstand vom 15. November 2026. Eine laufende Aktualisierung und ein historischer Verlauf sind noch nicht verbunden.'",
                "databody:'Datenstand: {datelong}. Der Wert wird regelmäßig aktualisiert. Ein historischer Verlauf ist noch nicht verbunden.',"
                "databodyPublic:'Historischer Wert vom {datelong}. Den aktuellen Marktstress siehst du nach der Anmeldung.'", "databody de")
    html = once(html, "databody:'This view uses the saved data snapshot from 15 November 2026. Continuous updates and a historical chart are not connected yet.'",
                "databody:'Data as of {datelong}. The score is updated regularly. A historical chart is not connected yet.',"
                "databodyPublic:'Historical reading from {datelong}. The latest market stress is available after sign-in.'", "databody en")
    html = once(html, "<p>${t('databody')}</p>", "<p>${t(window.InvestTimer?.member?'databody':'databodyPublic')}</p>", "databody Auswahl")
    html = once(html, "timestamp:'US-Aktienmarkt · Datenstand 15. Nov. 2026'", "timestamp:'US-Aktienmarkt · Datenstand {date}'", "timestamp de")
    html = once(html, "timestamp:'US stock market · Data as of 15 Nov 2026'", "timestamp:'US stock market · Data as of {date}'", "timestamp en")
    html = once(html, "const t=k=>copy[state.lang][k];\nconst number=",
                "const dateLabel=month=>{if(!result?.asOf)return '—';const [y,m,d]=result.asOf.split('-').map(Number);"
                "return new Date(Date.UTC(y,m-1,d)).toLocaleDateString(state.lang==='de'?'de-DE':'en-GB',{day:'numeric',month,year:'numeric',timeZone:'UTC'})};\n"
                "const t=k=>{const v=copy[state.lang][k];return typeof v==='string'?v.replace('{datelong}',()=>dateLabel('long')).replace('{date}',()=>dateLabel('short')):v};\n"
                "const number=", "t()")
    html = once(html, "try{result=evaluateSnapshot(JSON.parse(document.getElementById('investtimer-snapshot').textContent))}catch{result=null}",
                "try{result=normaliseResult(JSON.parse(document.getElementById('investtimer-result').textContent))}catch{result=null}", "Ergebnis laden")
    html = once(html, "render();\n\n})();\n(() => {\n/* 04 ·", "render();\n" + LIVE_JS + "\n})();\n(() => {\n/* 04 ·", "Live-Abruf")

    # Zugangs- und KI-Ansicht an echte Daten und den Chat anschliessen
    html = once(html, "/* UI concept only. No authentication, live feed or remote AI service. */",
                "/* Oeffentliche Ansicht und Ansicht nach Login. Noch keine echte Anmeldung: der Wechsel ist eine Darstellung. */", "Zugang Kommentar")
    html = once(html, "const snapshot=JSON.parse($('#investtimer-snapshot').textContent);\n"
                      "const manifest=JSON.parse($('#investtimer-export-manifest').textContent);\n"
                      "const score=manifest.snapshotScore;\n",
                "const IT=window.InvestTimer;\nconst view=()=>IT.view||{};\nconst score=()=>view().rounded??'—';\n", "Zugang Daten")
    html = once(html, "let member=false, opener=null, question='', answerKind='reading', turns=[];",
                "let member=false, opener=null, question='', turns=[], busy=false, tab=0;", "Zugang Zustand")
    html = once(html, "new Date(snapshot.asOf+'T12:00:00Z')", "new Date((view().asOf||'1970-01-01')+'T12:00:00Z')", "Zugang Datum")
    if html.count("+score+' / 100 · '") != 2:
        raise SystemExit("Erwartete zwei Stellen fuer die Wertanzeige im KI-Bereich")
    html = html.replace("+score+' / 100 · '", "+score()+' / 100 · '")
    if html.count("'+score+'") != 4:
        raise SystemExit("Erwartete vier Textstellen mit dem Wert")
    html = html.replace("'+score+'", "{score}")
    html = once(html, "const t=k=>c[lang()][k];", "const t=k=>String(c[lang()][k]).replace('{score}',score());", "Zugang t()")
    html = once(html, "const c={de:{login:'Anmelden',", "const c={de:{" + KEYS_DE + "login:'Anmelden',", "Texte de")
    html = once(html, "},en:{login:'Sign in',logout:'Sign out',preview:", "},en:{" + KEYS_EN + "login:'Sign in',logout:'Sign out',preview:", "Texte en")
    html = once(html, "stamp.textContent=(member?t('saved'):t('preview'))+' · '+date();stamp.title=member?t('memberNote'):t('noCurrent');",
                "stamp.textContent=(member?t('current'):t('preview'))+' · '+date();stamp.title=member?'':t('noCurrent');", "Stempel")
    html = once(html, "memberNote.textContent=t('memberNote');memberNote.hidden=!member;", "memberNote.hidden=true;", "Mitglieder-Hinweis")
    html = once(html, "$('.app-footer [data-i18n=\"timestamp\"]').textContent=t('source')+date();",
                "$('.app-footer [data-i18n=\"timestamp\"]').textContent=t(member?'sourceLive':'source')+date();", "Fusszeile")
    if html.count("t('chatNote')") != 2 or html.count('maxlength="2000"') != 2:
        raise SystemExit("Erwartete je zwei Stellen fuer chatNote und maxlength")
    html = html.replace("t('chatNote')", "t('aiNote')").replace('maxlength="2000"', 'maxlength="300"')
    html = once(html, "function switchView(value){member=value;question='';update();",
                "function switchView(value){member=value;question='';IT.setMember(value);update();", "Ansichtswechsel")

    # Texte des Entwurfs, die im Betrieb nicht mehr vorkommen (Beispielantworten, Vorschau-Hinweise)
    before, access = html.split('<script id="investtimer-access-ui">', 1)
    access, removed = re.subn(
        r"(?<=[,{])(?:sample|answer1|answer1b|answer2|answer2b|freeTitle|free|chatNote|memberNote|saved):'(?:[^'\\]|\\.)*',", "", access)
    if removed != 20:
        raise SystemExit("Erwartete 20 entfernte Entwurfstexte, gefunden %d" % removed)
    html = before + '<script id="investtimer-access-ui">' + access

    fragen = json.loads((ROOT / "volafly-api" / "investtimer_fragen.json").read_text(encoding="utf-8"))
    kategorien = [{"kurz": k["kurz"], "fragen": [f["frage"] for f in k["fragen"]]} for k in fragen["kategorien"]]
    html = sub_once(html, r"function answerMarkup\(kind\)\{.*?function closeChat\(\)\{[^\n]*\n",
                    CHAT_JS.replace("__FRAGEN__", json.dumps(kategorien, ensure_ascii=False)), "Chat-Kern")
    html = sub_once(html, r"document\.addEventListener\('submit',e=>\{if\(!\['assistant-entry-form'[^\n]*\n", SUBMIT_JS, "Chat-Absenden")
    html = once(html, "else if(b.dataset.ask)openChat(b.dataset.ask,null,b);",
                "else if(b.dataset.ask)openChat(t(b.dataset.ask==='composition'?'question2':'question1'),b);"
                "else if(b.dataset.more!==undefined)ask(b.dataset.more);"
                "else if(b.dataset.tab!==undefined){tab=Number(b.dataset.tab);renderChat(false);$('.assistant-messages').scrollTop=1e6}", "Chat-Klicks")
    html = once(html, "new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});\nupdate();",
                "new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});\n"
                "document.addEventListener('investtimer:update',update);\nupdate();", "Zugang Aktualisierung")

    # Stile: Mobil-Nachschaerfung hinter die Export-Stile, Ergaenzungen hinter die Zugangs-Stile
    head, rest = html.split('<style id="investtimer-access-style">', 1)
    head = once(head, "</style>", MOBILE_CSS + "</style>", "Mobil-CSS")
    access_css, rest = rest.split("</style>", 1)
    html = head + '<style id="investtimer-access-style">' + access_css + V12_CSS + "</style>" + rest

    for leftover in ("investtimer-snapshot", "evaluateSnapshot", "metricRows", "configRows", "Fear_Greed_Index",
                     "snapshotScore", "sourceLibraryFileId", "data:video", "answerKind", "BEISPIELANTWORT"):
        if leftover in html:
            raise SystemExit("Rest gefunden: " + leftover)
    (target / "index.html").write_text(html, encoding="utf-8")
    print("ok: oeffentlicher Rueckfall %s vom %s, %d Bytes HTML, Film %d Bytes" % (
        fallback["rounded"], fallback["asOf"], len(html.encode()), (target / "film" / "investtimer-49s.mp4").stat().st_size))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0], args[1], "--vorschau" in sys.argv)
