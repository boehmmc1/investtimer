/* Aktualitaet des Werts (angemeldet): Zeile ueber dem Wert "Aktualisiert vor {n} Min." (gerade eben / vor {n} Std.),
   laeuft jede Minute mit; "· US-Boerse geschlossen" ausserhalb der Handelszeit (Wochenende, US-Feiertage, vor 9:30 / nach 16:00 New York);
   waehrend der Handelszeit und aelter als 60 Min. dezent "Aktualisierung verzoegert". Ausgeloggt bleibt die Zeile wie bisher.
   Zeitpunkt: berechnetUm aus /api/aktuell (letzte erfolgreiche Berechnung). */
(()=>{
const AT={de:{jetzt:'Aktualisiert gerade eben',min:'Aktualisiert vor {n} Min.',std:'Aktualisiert vor {n} Std.',zu:'US-Börse geschlossen',spaet:'Aktualisierung verzögert'},
 en:{jetzt:'Updated just now',min:'Updated {n} min ago',std:'Updated {n} hr ago',zu:'US market closed',spaet:'Update delayed'}};
const at=k=>AT[document.documentElement.lang==='en'?'en':'de'][k];
/* NYSE-Feiertage (ganztaegig geschlossen) 2026/2027 */
const FEIERTAGE=new Set(['2026-01-01','2026-01-19','2026-02-16','2026-04-03','2026-05-25','2026-06-19','2026-07-03','2026-09-07','2026-11-26','2026-12-25',
 '2027-01-01','2027-01-18','2027-02-15','2027-03-26','2027-05-31','2027-06-18','2027-07-05','2027-09-06','2027-11-25','2027-12-24']);
function boerseOffen(jetzt){
 const t=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,weekday:'short'}).formatToParts(jetzt);
 const g=k=>(t.find(x=>x.type===k)||{}).value,tag=g('year')+'-'+g('month')+'-'+g('day'),min=Number(g('hour'))%24*60+Number(g('minute'));
 if(g('weekday')==='Sat'||g('weekday')==='Sun'||FEIERTAGE.has(tag))return false;
 return min>=570&&min<960;
}
IT.boerseOffen=boerseOffen;
function zeile(){
 const stamp=$('.snapshot-label');if(!stamp)return;
 const v=IT.member&&IT.live;const zeit=v&&Date.parse(v.berechnetUm||'');
 if(!v||!zeit){stamp.classList.remove('mit-aktualitaet');return}
 const jetzt=new Date(),alter=Math.max(0,Math.round((jetzt-zeit)/60000)),offen=boerseOffen(jetzt);
 const text=alter<1?at('jetzt'):alter<60?at('min').replace('{n}',alter):at('std').replace('{n}',Math.floor(alter/60));
 stamp.classList.add('mit-aktualitaet');
 stamp.innerHTML='<span>'+esc(text)+'</span>'+(!offen?'<span class="aktualitaet-zu"> · '+esc(at('zu'))+'</span>':'')
  +(offen&&alter>60?'<span class="aktualitaet-spaet"> · '+esc(at('spaet'))+'</span>':'');
 stamp.title=new Date(zeit).toLocaleString(document.documentElement.lang==='en'?'en-US':'de-DE',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
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
const ohneQuery=s=>String(s||'').replace(/\?[^\s:)]*/g,'');
function melden(meldung,datei,zeile,stack){
 meldung=String(meldung||'').slice(0,300);if(!meldung||anzahl>=5)return;
 const schluessel=meldung+'|'+datei+'|'+zeile;if(gesendet.has(schluessel))return;gesendet.add(schluessel);anzahl++;
 try{fetch('/api/fehler',{method:'POST',keepalive:true,cache:'no-store',credentials:'omit',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({meldung,datei:ohneQuery(datei).slice(0,200),zeile:zeile||0,stack:ohneQuery(stack).slice(0,1500),
   ansicht:(location.hash.replace('#','')||'start').slice(0,20),version:window.INVESTTIMER_VERSION||'',geraet:geraet()})}).catch(()=>{})}catch{}
}
addEventListener('error',e=>{if(!e.message)return;melden(e.message,e.filename,e.lineno,e.error&&e.error.stack)});
addEventListener('unhandledrejection',e=>{const r=e.reason;melden(r&&r.message?r.message:String(r),'',0,r&&r.stack)});
IT.fehlerMelden=melden;
})();
