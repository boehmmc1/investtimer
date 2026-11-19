/* Updates der installierten Web-App und Offline-Hinweis (Service Worker: tools/sw.js).
   - beim Oeffnen und bei jeder Rueckkehr in die App (visibilitychange) fragt die Seite nach einer neuen Version
   - neue Version aktiv: sofort neu laden, wenn kein Dialog, kein KI-Gespraech und keine Eingabe offen ist,
     sonst Hinweis "Neue Version verfuegbar · Aktualisieren" (wird beim naechsten ruhigen Moment automatisch erledigt)
   - offline: "Offline · Stand {Zeit}" (Zeit des zuletzt geladenen Werts) */
(()=>{
const UT={de:{neu:'Neue Version verfügbar',aktualisieren:'Aktualisieren',offline:'Offline · Stand {z}',offlineOhne:'Offline'},
 en:{neu:'New version available',aktualisieren:'Update',offline:'Offline · as of {z}',offlineOhne:'Offline'}};
const ut=k=>UT[document.documentElement.lang==='en'?'en':'de'][k];
const leiste=document.createElement('div');leiste.className='it-hinweisleiste';leiste.setAttribute('role','status');leiste.setAttribute('aria-live','polite');leiste.hidden=true;
document.body.append(leiste);
let zustand=null;/* 'neu' | 'offline' | null */
function zeigen(){
 if(zustand==='neu'){leiste.innerHTML='<span>'+esc(ut('neu'))+'</span><span aria-hidden="true">·</span><button type="button" data-update="jetzt">'+esc(ut('aktualisieren'))+'</button>';leiste.hidden=false}
 else if(zustand==='offline'){let z='';try{const t=Number(localStorage.getItem('investtimer-stand-zeit'));if(t)z=new Date(t).toLocaleString(document.documentElement.lang==='en'?'en-US':'de-DE',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}catch{}
  leiste.innerHTML='<span>'+esc(z?ut('offline').replace('{z}',z):ut('offlineOhne'))+'</span>';leiste.hidden=false}
 else leiste.hidden=true;
 document.body.classList.toggle('mit-hinweisleiste',!leiste.hidden);
}
leiste.addEventListener('click',e=>{if(e.target.closest('[data-update]'))location.reload()});
const ruhig=()=>!document.querySelector('dialog[open]')&&!(IT.kiGespraechAktiv&&IT.kiGespraechAktiv())&&!(document.activeElement&&document.activeElement.matches('input,textarea,select'));
let neuBereit=false;
function neueVersion(){if(neuBereit)return;neuBereit=true;if(ruhig()&&document.visibilityState==='visible'){location.reload();return}zustand='neu';zeigen()}
/* ruhiger Moment spaeter: beim Wechsel in den Hintergrund und zurueck, oder nachdem ein Dialog geschlossen wurde */
document.addEventListener('visibilitychange',()=>{if(neuBereit&&document.visibilityState==='visible'&&ruhig())location.reload()});
if('serviceWorker' in navigator&&!window.InvestTimerApp){
 /* Erste Uebernahme (Seite war noch ohne Service Worker) ist kein Update; jede weitere ist eine neue Version */
 let gesteuert=!!navigator.serviceWorker.controller;
 navigator.serviceWorker.addEventListener('controllerchange',()=>{if(gesteuert)neueVersion();else gesteuert=true});
 const pruefen=()=>navigator.serviceWorker.getRegistration().then(r=>r&&r.update()).catch(()=>{});
 setTimeout(pruefen,3000);
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')pruefen()});
 IT.updatePruefen=pruefen;
}
function netz(){if(!navigator.onLine){if(zustand!=='neu'){zustand='offline';zeigen()}}else if(zustand==='offline'){IT.loadLive&&IT.loadLive(true)}}
addEventListener('online',netz);addEventListener('offline',netz);netz();
/* verlaesslicher als navigator.onLine: der Wert kam aus dem Speicher des Service Workers */
document.addEventListener('investtimer:offline',()=>{if(zustand!=='neu'){zustand='offline';zeigen()}});
document.addEventListener('investtimer:online',()=>{if(zustand==='offline'){zustand=null;zeigen()}});
if(IT.offline&&zustand!=='neu'){zustand='offline';zeigen()}
new MutationObserver(()=>{if(zustand)zeigen()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
})();
