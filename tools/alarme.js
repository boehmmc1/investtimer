/* Alarme mit eigener Schwelle, Web-Push und Installationshinweis */
const istIOS=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const installiert=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
const nativ=()=>window.InvestTimerApp&&window.InvestTimerApp.push;
const pushMoeglich=()=>'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window;
let nurPush=false,alarmKanal=null,swReg=null,installPrompt=null,alarmDaten=null,alarmHinweis='',pushZustand='laedt',alarmOpener=null;
if(!window.InvestTimerApp&&'serviceWorker' in navigator&&(location.protocol==='https:'||location.hostname==='127.0.0.1')){
 navigator.serviceWorker.register('/sw.js').then(r=>{swReg=r}).catch(()=>{});
 navigator.serviceWorker.addEventListener('message',e=>{if(e.data&&e.data.typ==='investtimer-neu-laden')IT.loadLive(true)});
}
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;installLink()});
window.addEventListener('appinstalled',()=>{installPrompt=null;installLink()});
const b64=s=>{const r=atob((s+'='.repeat((4-s.length%4)%4)).replace(/-/g,'+').replace(/_/g,'/'));return Uint8Array.from(r,c=>c.charCodeAt(0))};
async function api(pfad,opt={}){
 const tok=await IT.token();if(!tok)throw 'login';
 const r=await fetch('/api/'+pfad,{...opt,cache:'no-store',headers:{'Content-Type':'application/json',Authorization:'Bearer '+tok}});
 const d=await r.json().catch(()=>({}));if(!r.ok)throw d.error||r.status;return d;
}
async function pushStatus(){
 if(nativ())return nativ().status();
 if(!pushMoeglich())return istIOS&&!installiert()?'ios':'nein';
 if(Notification.permission==='denied')return 'blockiert';
 const reg=swReg||await navigator.serviceWorker.getRegistration();const abo=reg&&await reg.pushManager.getSubscription();
 return abo?'aktiv':'aus';
}
async function pushEinschalten(erlaubt){
 if(nativ()){const tok=await nativ().einschalten();if(!tok)return false;alarmDaten=await api('push/geraet',{method:'POST',body:JSON.stringify({apns:tok})});return true}
 if(!erlaubt&&await Notification.requestPermission()!=='granted')return false;
 if(!alarmDaten||!alarmDaten.vapid)alarmDaten=await api('alarme');
 const reg=swReg||await navigator.serviceWorker.ready;
 const abo=await reg.pushManager.getSubscription()||await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64(alarmDaten.vapid)});
 alarmDaten=await api('push/geraet',{method:'POST',body:JSON.stringify(abo.toJSON())});return true;
}
const teilen='<svg class="teilen" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-label="Teilen"><path d="M10 12.5V2.5M6.5 6 10 2.5 13.5 6"/><path d="M6 9H4.5v8.5h11V9H14"/></svg>';
const iosSchritte=()=>'<ol class="install-schritte"><li>'+t('ios1').replace('{teilen}',teilen)+'</li><li>'+t('ios2')+'</li><li>'+t('ios3')+'</li></ol>';
function pushBox(){
 switch(pushZustand){
  case 'aktiv':return '<p><b>'+t('pushAktiv')+'</b></p><div class="access-more"><button type="button" class="text-button" id="push-test">'+t('pushTest')+'</button><button type="button" class="text-button" id="push-aus">'+t('pushAus')+'</button></div><div id="push-test-status" class="push-test-status" role="status" aria-live="polite"></div>';
  case 'aus':return '<p>'+t('pushAusText')+'</p><button type="button" class="primary full" id="push-an">'+t('pushAn')+'</button>';
  case 'blockiert':return '<p>'+t('pushBlockiert')+'</p>';
  case 'ios':return '<p><b>'+t('iosTitel')+'</b></p>'+iosSchritte();
  case 'nein':return '<p>'+t('pushNein')+'</p>';
  default:return '<p>'+t('alarmLaedt')+'</p>';
 }
}
const alarmDlg=document.createElement('dialog');alarmDlg.id='alarm-dialog';alarmDlg.className='modal access-dialog alarm-dialog';alarmDlg.setAttribute('aria-labelledby','alarm-title');document.body.append(alarmDlg);
function alarmStatus(a){
 if(!a.aktiv)return t('alarmPausiert');
 if(a.scharf===false)return t(a.richtung==='ueber'?'alarmWartetUeber':'alarmWartetUnter').replace('{x}',a.schwelle);
 return t('alarmAktiv');
}
/* Erklaerung unter dem Regler, live mit dem angezeigten Wert */
function alarmErklaerung(){
 const x=Number(($('#alarm-wert')||{}).value),r=($('#alarm-richtung')||{}).value||'ueber',w=Number(view().rounded),el=$('#alarm-erklaerung');
 if(!el||!x)return;const bekannt=Number.isFinite(w)&&view().rounded!==null&&view().rounded!==undefined;
 const schon=bekannt&&(r==='ueber'?w>x:w<x);
 el.textContent=t(r==='ueber'?(schon?'alarmErklUeberSchon':'alarmErklUeber'):(schon?'alarmErklUnterSchon':'alarmErklUnter'))
  .replace(/\{x\}/g,x).replace('{x1}',r==='ueber'?x+1:x-1).replace('{w}',w);
}
const kanalStandard=()=>alarmKanal||(['aktiv','aus'].includes(pushZustand)?'push':'email');
function renderAlarme(){
 const d=alarmDaten,liste=(d&&d.alarme)||[],voll=d&&!d.fehler&&liste.length>=(d.max||5);
 const v=Math.min(99,Math.max(1,(Number(view().rounded)||50)+10));
 const eintraege=!d?'<p class="alarm-leer">'+t('alarmLaedt')+'</p>':d.fehler?'<p class="access-error">'+t('alarmFehler')+'</p>':liste.length
  ?'<ul class="alarm-liste">'+liste.map(a=>'<li class="alarm-eintrag'+(a.aktiv?'':' pausiert')+'"><span class="alarm-text"><b>'+t(a.richtung==='ueber'?'alarmUeber':'alarmUnter')+' '+a.schwelle+'</b><small>'+esc(alarmStatus(a))+'</small></span>'
   +'<label class="alarm-schalter"><input type="checkbox" role="switch" data-alarm-aktiv="'+a.id+'"'+(a.aktiv?' checked':'')+' aria-label="'+t('alarmAktiv')+': '+t(a.richtung==='ueber'?'alarmUeber':'alarmUnter')+' '+a.schwelle+'"><span class="spur" aria-hidden="true"></span></label>'
   +'<select class="alarm-kanal-wahl" data-alarm-kanal="'+a.id+'" aria-label="'+t('alarmKanal')+': '+a.schwelle+'">'+['push','email','beide'].map(k=>'<option value="'+k+'"'+(a.kanal===k?' selected':'')+'>'+t('kanal_'+k)+'</option>').join('')+'</select>'
   +'<button type="button" class="text-button" data-alarm-weg="'+a.id+'" aria-label="'+t('alarmLoeschen')+': '+a.schwelle+'">'+t('alarmLoeschen')+'</button></li>').join('')+'</ul>'
  :'<p class="alarm-leer">'+t('alarmKeine')+'</p>';
 const form=voll||!d||d.fehler?'':'<form id="alarm-form" class="access-form alarm-form" novalidate><label for="alarm-richtung">'+t('alarmWenn')+'</label>'
  +'<select id="alarm-richtung"><option value="ueber">'+t('alarmSteigt')+'</option><option value="unter">'+t('alarmFaellt')+'</option></select>'
  +'<div class="alarm-schwelle"><label for="alarm-wert">'+t('alarmSchwelle')+'</label><output id="alarm-ausgabe" for="alarm-wert">'+v+'</output></div>'
  +'<input id="alarm-wert" type="range" min="1" max="99" value="'+v+'" aria-describedby="alarm-erklaerung"><p class="alarm-erklaerung" id="alarm-erklaerung" aria-live="polite"></p>'
  +'<fieldset class="alarm-kanal"><legend>'+t('alarmKanal')+'</legend>'+['push','email','beide'].map(k=>'<label class="wahl"><input type="radio" name="alarm-kanal" value="'+k+'"'+(kanalStandard()===k?' checked':'')+'> '+t('kanal_'+k)+'</label>').join('')+'</fieldset>'
  +'<p class="alarm-mailhinweis">'+esc(t('alarmMailAn')).replace('{email}','<b>'+esc((IT.emailVonSitzung&&IT.emailVonSitzung())||'')+'</b>')+'</p>'
  +'<p class="access-error" id="alarm-fehler" role="alert">'+esc(alarmHinweis)+'</p>'
  +'<button class="primary full" type="submit">'+t('alarmSpeichern')+'</button></form>';
 alarmDlg.innerHTML='<div class="modal-top"><span class="eyebrow">'+t('alarmEyebrow')+'</span><button class="close-button" id="close-alarm" type="button" aria-label="'+t('close')+'">×</button></div>'
  +'<h2 id="alarm-title" tabindex="-1">'+t('alarmTitle')+'</h2><p>'+t('alarmIntro')+'</p>'
  +'<div class="push-box">'+pushBox()+'</div>'+(nurPush?'':eintraege+form+(voll?'<p class="preview-notice">'+t('alarmMax')+'</p>':'')+'<p class="preview-notice">'+t('alarmRegel')+'</p>');
 alarmErklaerung();
}
async function oeffneAlarme(opener,nurMitteilungen){
 nurPush=!!nurMitteilungen;alarmOpener=opener;alarmHinweis='';pushZustand='laedt';renderAlarme();alarmDlg.showModal();document.body.classList.add('access-open');$('#alarm-title').focus({preventScroll:true});
 try{alarmDaten=await api('alarme')}catch(x){if(x==='login'||x===401){schliesseAlarme();IT.abmelden();return}alarmDaten={fehler:true}}
 pushZustand=await pushStatus().catch(()=>'nein');renderAlarme();
}
function schliesseAlarme(){if(alarmDlg.open)alarmDlg.close();document.body.classList.remove('access-open');alarmOpener?.focus({preventScroll:true})}
document.addEventListener('click',e=>{const b=e.target.closest('#open-subscribe,#create-alert');if(!b||!IT.member)return;e.preventDefault();e.stopImmediatePropagation();IT.alarmListe?IT.alarmListe(b):oeffneAlarme(b)},true);
alarmDlg.addEventListener('cancel',e=>{e.preventDefault();schliesseAlarme()});
alarmDlg.addEventListener('click',async e=>{
 if(e.target===alarmDlg){const r=alarmDlg.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)schliesseAlarme();return}
 const b=e.target.closest('button');if(!b)return;
 if(b.id==='close-alarm')schliesseAlarme();
 else if(b.id==='push-an'){b.disabled=true;try{await pushEinschalten()}catch{}pushZustand=await pushStatus().catch(()=>'nein');renderAlarme()}
 else if(b.id==='push-aus'&&nativ()){b.disabled=true;try{const tok=await nativ().aus();if(tok)alarmDaten=await api('push/geraet-entfernen',{method:'POST',body:JSON.stringify({endpoint:'apns:'+tok})})}catch{}pushZustand=await pushStatus().catch(()=>'nein');renderAlarme()}
 else if(b.id==='push-aus'){b.disabled=true;try{const reg=swReg||await navigator.serviceWorker.getRegistration(),abo=reg&&await reg.pushManager.getSubscription();
  if(abo){alarmDaten=await api('push/geraet-entfernen',{method:'POST',body:JSON.stringify({endpoint:abo.endpoint})});await abo.unsubscribe()}}catch{}pushZustand=await pushStatus().catch(()=>'nein');renderAlarme()}
 else if(b.id==='push-test')pushTest(b);
 else if(b.dataset.alarmWeg){b.disabled=true;alarmDaten=await api('alarme/'+b.dataset.alarmWeg,{method:'DELETE'}).catch(()=>alarmDaten);renderAlarme();$('#alarm-title').focus({preventScroll:true})}
});
alarmDlg.addEventListener('change',async e=>{
 if(e.target.id==='alarm-richtung'){alarmErklaerung();return}
 if(e.target.name==='alarm-kanal'){alarmKanal=e.target.value;return}
 const kid=e.target.dataset.alarmKanal;
 if(kid){e.target.disabled=true;alarmDaten=await api('alarme/'+kid,{method:'PATCH',body:JSON.stringify({kanal:e.target.value,sprache:document.documentElement.lang})}).catch(()=>alarmDaten);renderAlarme();$('[data-alarm-kanal="'+kid+'"]')?.focus();
  if(e.target.value!=='email'&&pushZustand==='aus'&&!nativ()&&window.Notification&&Notification.permission==='default'){try{if(await Notification.requestPermission()==='granted'){await pushEinschalten(true);pushZustand=await pushStatus();renderAlarme()}}catch{}}
  return}
 const id=e.target.dataset.alarmAktiv;if(!id)return;e.target.disabled=true;
 alarmDaten=await api('alarme/'+id,{method:'PATCH',body:JSON.stringify({aktiv:e.target.checked,sprache:document.documentElement.lang})}).catch(()=>alarmDaten);renderAlarme();$('[data-alarm-aktiv="'+id+'"]')?.focus()});
alarmDlg.addEventListener('input',e=>{if(e.target.id==='alarm-wert'){$('#alarm-ausgabe').textContent=e.target.value;alarmErklaerung()}});
alarmDlg.addEventListener('submit',async e=>{e.preventDefault();
 const kanal=(alarmDlg.querySelector('input[name=alarm-kanal]:checked')||{}).value||'push';alarmKanal=kanal;
 const frage=kanal==='email'?null:nativ()?(pushZustand==='aus'?Promise.resolve('nativ'):null):pushZustand==='aus'&&window.Notification&&Notification.permission==='default'?Notification.requestPermission():null;
 const knopf=e.target.querySelector('button[type=submit]');knopf.disabled=true;alarmHinweis='';
 try{alarmDaten=await api('alarme',{method:'POST',body:JSON.stringify({richtung:$('#alarm-richtung').value,schwelle:Number($('#alarm-wert').value),kanal,sprache:document.documentElement.lang})})}
 catch(x){alarmHinweis=t(x==='doppelt'?'alarmDoppelt':x==='max'?'alarmMax':x==='email'?'alarmMailFehlt':'alarmFehler');knopf.disabled=false;$('#alarm-fehler').textContent=alarmHinweis;return}
 if(frage){try{const f=await frage;if(f==='granted'||f==='nativ')await pushEinschalten(true)}catch{}}
 pushZustand=await pushStatus().catch(()=>'nein');renderAlarme();$('#alarm-title').focus({preventScroll:true});
});
/* Testnachricht mit Empfangsbestaetigung: Push-Dienst nimmt an (Server) -> Geraet zeigt an (Service Worker/App) */
const pushHinweise=()=>'<ul class="push-hinweise"><li>'+t('pushHinweisOs')+'</li><li>'+t('pushHinweisFokus')+'</li><li>'+t('pushHinweisIos')+'</li><li>'+t('pushHinweisBrowser')+'</li></ul>';
async function pushTest(b){
 b.disabled=true;
 const zeige=(html,art)=>{const s=$('#push-test-status');if(s){s.innerHTML=html;s.className='push-test-status '+(art||'')}};
 zeige(t('pushTestSendet'));
 const angekommen=new Promise(res=>{
  let tm;const h=e=>{if(e.data&&e.data.typ==='investtimer-push'&&e.data.tag==='investtimer-test'){weg();res(true)}},hn=()=>{weg();res(true)};
  const weg=()=>{clearTimeout(tm);navigator.serviceWorker&&navigator.serviceWorker.removeEventListener('message',h);window.removeEventListener('investtimer-push-angekommen',hn)};
  navigator.serviceWorker&&navigator.serviceWorker.addEventListener('message',h);window.addEventListener('investtimer-push-angekommen',hn);
  tm=setTimeout(()=>{weg();res(false)},15000);
 });
 let d;
 try{d=await api('push/test',{method:'POST',body:JSON.stringify({sprache:document.documentElement.lang})})}
 catch(x){zeige(t(x==='warten'?'pushTestWarten':'alarmFehler'),'fehler');b.disabled=false;return}
 if(!d.angenommen){zeige(t(d.abgemeldet?'pushTestAbgemeldet':d.geraete===0?'pushTestKeinGeraet':'pushTestAbgelehnt'),'fehler');b.disabled=false;return}
 zeige(t('pushTestAngenommen'));
 const ok=await angekommen;
 zeige(ok?'<b>'+t('pushTestZugestellt')+'</b><details><summary>'+t('pushTestTrotzdem')+'</summary>'+pushHinweise()+'</details>'
  :'<b>'+t('pushTestNicht')+'</b><p>'+t('pushTestNichtText')+'</p>'+pushHinweise(),ok?'ok':'warnung');
 b.disabled=false;
}
/* App installieren: Eintrag im Kontomenue (kontomenue.js) und Anleitung je Geraet */
const installDlg=document.createElement('dialog');installDlg.id='install-dialog';installDlg.className='modal access-dialog';installDlg.setAttribute('aria-labelledby','install-title');document.body.append(installDlg);
function installLink(){document.dispatchEvent(new Event('investtimer:kontomenue'))}
IT.installierbar=()=>!installiert()&&!window.InvestTimerApp;
IT.oeffneInstall=o=>oeffneInstall(o);
IT.oeffneMitteilungen=o=>oeffneAlarme(o,true);
function oeffneInstall(opener){
 alarmOpener=opener;
 const inhalt=istIOS?'<p>'+t('installIOS')+'</p>'+iosSchritte()
  :installPrompt?'<p>'+t('installAndroid')+'</p><button type="button" class="primary full" id="install-jetzt">'+t('installJetzt')+'</button>'
  :'<p>'+t('installAndere')+'</p>';
 installDlg.innerHTML='<div class="modal-top"><span class="eyebrow">INVESTTIMER</span><button class="close-button" id="close-install" type="button" aria-label="'+t('close')+'">×</button></div>'
  +'<h2 id="install-title" tabindex="-1">'+t('installTitel')+'</h2>'+inhalt+'<p class="preview-notice">'+t('installPush')+'</p>';
 installDlg.showModal();document.body.classList.add('access-open');$('#install-title').focus({preventScroll:true});
}
function schliesseInstall(){if(installDlg.open)installDlg.close();document.body.classList.remove('access-open');alarmOpener?.focus({preventScroll:true})}
document.addEventListener('click',e=>{if(e.target.closest('#install-link'))oeffneInstall(e.target.closest('#install-link'))});
installDlg.addEventListener('cancel',e=>{e.preventDefault();schliesseInstall()});
installDlg.addEventListener('click',async e=>{
 if(e.target===installDlg){const r=installDlg.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)schliesseInstall();return}
 const b=e.target.closest('button');if(!b)return;
 if(b.id==='close-install')schliesseInstall();
 else if(b.id==='install-jetzt'&&installPrompt){installPrompt.prompt();await installPrompt.userChoice.catch(()=>null);installPrompt=null;schliesseInstall();installLink()}
});
installLink();document.addEventListener('investtimer:update',installLink);
new MutationObserver(installLink).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
