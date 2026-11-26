/* Aktualitaet des Werts (angemeldet): Zeile ueber dem Wert mit zwei Zustaenden.
   a) "Aktualisiert" (gruener Punkt): letzte erfolgreiche Berechnung (berechnetUm aus /api/aktuell) hoechstens AKT_MAX alt.
   b) "Nicht aktualisiert · Stand {Datum, Uhrzeit Europe/Berlin}" (Ocker): aelter oder letzter Abruf fehlgeschlagen.
   Die Pipeline rechnet alle 30 Minuten (Lauf dauert einige Minuten), daher 45 Minuten Grenze; gilt auch am Wochenende.
   Neu geprueft bei jeder Rueckkehr in die App und alle 10 Minuten (update.js), dazu jede Minute fuer den Zeitablauf.
   Ausgeloggt bleibt die Zeile wie bisher. */
(()=>{
const AKT_MAX=45*60000;
const AT={de:{ok:'Aktualisiert',alt:'Nicht aktualisiert',stand:'Stand {d}'},en:{ok:'Up to date',alt:'Not updated',stand:'as of {d}'}};
const en=()=>document.documentElement.lang==='en',at=k=>AT[en()?'en':'de'][k];
function stand(ms){
 const t=new Intl.DateTimeFormat(en()?'en-US':'de-DE',{timeZone:'Europe/Berlin',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(new Date(ms));
 const g=k=>(t.find(x=>x.type===k)||{}).value||'',uhr=g('hour').replace(/^24$/,'00')+':'+g('minute');
 return en()?g('month')+' '+g('day')+', '+g('year')+', '+uhr:g('day')+'. '+g('month')+' '+g('year')+', '+uhr;
}
IT.aktualitaetStand=stand;
function zeile(){
 const stamp=$('.snapshot-label');if(!stamp)return;
 const v=IT.live||IT.gespeichert,zeit=v&&Date.parse(v.berechnetUm||'');
 if(!IT.member||!IT.live&&!IT.liveFehler){stamp.classList.remove('mit-aktualitaet');return}
 const frisch=!!IT.live&&!IT.liveFehler&&zeit&&Date.now()-zeit<=AKT_MAX;
 stamp.classList.add('mit-aktualitaet');stamp.removeAttribute('title');
 stamp.innerHTML='<span class="aktualitaet-punkt '+(frisch?'ok':'alt')+'" aria-hidden="true"></span><span>'+esc(at(frisch?'ok':'alt')+(!frisch&&zeit?' · '+at('stand').replace('{d}',stand(zeit)):''))+'</span>';
}
IT.aktualitaet=zeile;
document.addEventListener('investtimer:update',zeile);
new MutationObserver(zeile).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
setInterval(zeile,60000);
zeile();
})();
/* Fehlermeldungen aus dem Browser an /api/fehler: Meldung, Datei/Zeile, gekuerzter Stack ohne Query-Strings, Ansicht, Version, Geraet grob.
   Keine E-Mail, keine Nutzer-ID, keine Eingabetexte. Hoechstens 5 Meldungen je Seitenaufruf, gleiche nur einmal. */
(()=>{
const gesendet=new Set();let anzahl=0;
const geraet=()=>{const u=navigator.userAgent,ios=/iPhone|iPad|iPod/.test(u)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1),
 android=/Android/.test(u),browser=/Edg\//.test(u)?'Edge':/Firefox\//.test(u)?'Firefox':/Chrome\//.test(u)?'Chrome':/Safari\//.test(u)?'Safari':'anderer Browser',
 inst=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 return (ios?'iOS':android?'Android':/Mac/.test(u)?'macOS':/Windows/.test(u)?'Windows':'Desktop')+' '+browser+(inst?', installiert':'')};
/* Umfeld ohne Personenbezug und ohne Kennung (Block E): Anzahl Wert/Bogen im DOM, Seitenuebersetzung, Erweiterung im Stack,
   Automatisierung, Sichtbarkeit, nur Host des Referrers */
const umfeld=stack=>{const h=document.documentElement,ref=(()=>{try{return document.referrer?new URL(document.referrer).host:''}catch{return ''}})();
 return {score:document.querySelectorAll('.score').length,stage:document.querySelectorAll('.gauge-stage').length,
  uebersetzt:/translated-(ltr|rtl)/.test(h.className)?'ja':'nein',erweiterung:/(chrome|moz)-extension:\/\//.test(String(stack||''))?'ja':'nein',
  webdriver:navigator.webdriver?'ja':'nein',sichtbar:document.visibilityState,ref:ref.slice(0,80)}};
const ohneQuery=s=>String(s||'').replace(/\?[^\s:)]*/g,'');
function melden(meldung,datei,zeile,stack){
 meldung=String(meldung||'').slice(0,300);if(!meldung||anzahl>=5)return;
 const schluessel=meldung+'|'+datei+'|'+zeile;if(gesendet.has(schluessel))return;gesendet.add(schluessel);anzahl++;
 try{fetch('/api/fehler',{method:'POST',keepalive:true,cache:'no-store',credentials:'omit',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({meldung,datei:ohneQuery(datei).slice(0,200),zeile:zeile||0,stack:ohneQuery(stack).slice(0,1500),
   ansicht:(location.hash.replace('#','')||'start').slice(0,20),version:window.INVESTTIMER_VERSION||'',geraet:geraet(),umfeld:umfeld(stack)})}).catch(()=>{})}catch{}
}
addEventListener('error',e=>{if(!e.message)return;melden(e.message,e.filename,e.lineno,e.error&&e.error.stack)});
addEventListener('unhandledrejection',e=>{const r=e.reason;melden(r&&r.message?r.message:String(r),'',0,r&&r.stack)});
IT.fehlerMelden=melden;
/* Anzeige fehlt (Block E): einmalig melden, auch fuer Faelle vor dem Laden dieses Teils */
window.ITMeldeFehlt=sel=>melden('Anzeige fehlt im DOM','',0,'fehlt: '+String(sel).slice(0,60));
(window.ITFehltWarte||[]).splice(0).forEach(s=>window.ITMeldeFehlt(s));
})();
