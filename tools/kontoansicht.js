/* Konto als eigene Ansicht (#konto), erreichbar ueber den Tab "Konto" (mobil) und "Mein Konto" im Kontomenue (Desktop).
   Angemeldet: E-Mail, registriert seit, Meine Alarme, Sprache, App installieren, Mein Konto (E-Mail aendern, Daten
   herunterladen, ueberall abmelden, Konto loeschen), Abo nur mit Paywall-Schalter, Abmelden, Fusszeile mit Version.
   Ausgeloggt: kurzer Satz, Anmelden, Sprache, Rechtliches. */
(()=>{
const KA={de:{
 eyebrow:'DEIN KONTO',titel:'Konto',titelAus:'Konto',ausSatz:'Melde dich an, um den aktuellen Wert zu sehen, die KI zu fragen und Alarme einzurichten.',
 anmelden:'Anmelden',email:'E-Mail',seit:'Registriert seit',alarme:'Meine Alarme',alarmNeu:'Alarm einrichten',alarmKeine:'Noch kein Alarm angelegt.',
 alarmUeber:'Steigt über {x}',alarmUnter:'Fällt unter {x}',stAktiv:'aktiv',stWartet:'wartet',stPausiert:'pausiert',
 kanal_push:'Push',kanal_email:'E-Mail',kanal_beide:'Push und E-Mail',
 sprache:'Sprache',installTitel:'App',install:'App installieren',installText:'InvestTimer vom Home-Bildschirm starten, mit Push-Mitteilungen für deine Alarme.',
 mein:'Mein Konto',emailAendern:'E-Mail-Adresse ändern',emailNeu:'Neue E-Mail-Adresse',emailSpeichern:'Bestätigung senden',
 emailGesendet:'Wir haben dir eine Bestätigung geschickt. Die neue Adresse gilt, sobald du den Link in der E-Mail öffnest.',
 emailGleich:'Das ist schon deine Adresse.',emailVergeben:'Diese Adresse gehört schon zu einem anderen Konto.',
 export:'Meine Daten herunterladen',exportText:'Eine Datei mit deinem Konto, deinen Alarmen und deiner KI-Nutzung.',
 ueberall:'Überall abmelden',ueberallText:'Meldet dich auf allen Geräten ab, auch hier.',
 passwort:'Passwort ändern',loeschen:'Konto löschen',abo:'Abo',abmelden:'Abmelden',
 impressum:'Impressum',datenschutz:'Datenschutz',version:'Version {v} · {d}',fehler:'Das hat nicht geklappt. Bitte versuche es gleich noch einmal.',laedt:'Wird geladen …'
},en:{
 eyebrow:'YOUR ACCOUNT',titel:'Account',titelAus:'Account',ausSatz:'Sign in to see the latest reading, ask the AI and set up alerts.',
 anmelden:'Sign in',email:'Email',seit:'Member since',alarme:'My alerts',alarmNeu:'Set up an alert',alarmKeine:'No alerts yet.',
 alarmUeber:'Rises above {x}',alarmUnter:'Falls below {x}',stAktiv:'active',stWartet:'waiting',stPausiert:'paused',
 kanal_push:'Push',kanal_email:'Email',kanal_beide:'Push and email',
 sprache:'Language',installTitel:'App',install:'Install app',installText:'Start InvestTimer from your home screen, with push notifications for your alerts.',
 mein:'Account settings',emailAendern:'Change email address',emailNeu:'New email address',emailSpeichern:'Send confirmation',
 emailGesendet:'We sent you a confirmation. The new address applies once you open the link in that email.',
 emailGleich:'That is already your address.',emailVergeben:'This address already belongs to another account.',
 export:'Download my data',exportText:'A file with your account, your alerts and your AI usage.',
 ueberall:'Sign out everywhere',ueberallText:'Signs you out on all devices, including this one.',
 passwort:'Change password',loeschen:'Delete account',abo:'Subscription',abmelden:'Sign out',
 impressum:'Legal notice',datenschutz:'Privacy',version:'Version {v} · {d}',fehler:'That did not work. Please try again in a moment.',laedt:'Loading …'
}};
const ka=k=>(KA[document.documentElement.lang==='en'?'en':'de'][k])||k;
const angemeldet=()=>!!(IT.member&&(IT.session||(IT.emailVonSitzung&&IT.emailVonSitzung())));
const VERSION=__VERSION__;
const zustand={nutzer:null,alarme:null,konto:null,meldung:'',meldungOk:false,laedt:false};
const sicht=document.createElement('section');sicht.id='konto-ansicht';sicht.className='konto-ansicht';sicht.hidden=true;sicht.setAttribute('aria-labelledby','konto-ansicht-titel');
($('#ki-ansicht')||$('.app-header'))?.after(sicht);
const datumLang=iso=>iso?new Date(iso).toLocaleDateString(document.documentElement.lang==='en'?'en-US':'de-DE',{day:'numeric',month:'long',year:'numeric'}):'—';
const pfeil='<svg class="konto-zeile-pfeil" viewBox="0 0 20 20" aria-hidden="true"><path d="m8 5 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
function sprachwahl(){
 const l=document.documentElement.lang==='en'?'en':'de';
 return '<div class="konto-block"><label class="konto-h" for="konto-sprache">'+ka('sprache')+'</label><select id="konto-sprache" class="konto-select"><option value="de"'+(l==='de'?' selected':'')+'>Deutsch</option><option value="en"'+(l==='en'?' selected':'')+'>English</option></select></div>';
}
function fuss(){
 const v=VERSION.v?'<span class="konto-version">'+esc(ka('version').replace('{v}',VERSION.v).replace('{d}',VERSION.d))+'</span>':'';
 return '<p class="konto-fuss"><a href="/impressum.html">'+ka('impressum')+'</a><span aria-hidden="true"> · </span><a href="/datenschutz.html">'+ka('datenschutz')+'</a>'+'</p>'+(v?'<p class="konto-fuss konto-fuss-version">'+v+'</p>':'');
}
function alarmZeile(a){
 const st=!a.aktiv?'pausiert':a.scharf===false?'wartet':'aktiv';
 const titel=ka(a.richtung==='ueber'?'alarmUeber':'alarmUnter').replace('{x}',a.schwelle);
 const sub=(typeof alarmStatus==='function'&&st==='wartet'?alarmStatus(a):'')||ka('kanal_'+(a.kanal||'push'));
 return '<li><button type="button" class="konto-zeile konto-alarm" data-konto="alarme"><span class="konto-zeile-text"><b>'+esc(titel)+'</b><small>'+esc(sub)+'</small></span>'
  +'<span class="konto-st st-'+st+'">'+ka(st==='aktiv'?'stAktiv':st==='wartet'?'stWartet':'stPausiert')+'</span>'+pfeil+'</button></li>';
}
function alarmBlock(){
 const d=zustand.alarme;let inhalt;
 if(!d)inhalt='<p class="konto-leise">'+ka('laedt')+'</p>';
 else if(d.fehler)inhalt='<p class="konto-leise">'+ka('fehler')+'</p>';
 else if(!d.alarme.length)inhalt='<p class="konto-leise">'+ka('alarmKeine')+'</p>';
 else inhalt='<ul class="konto-liste">'+d.alarme.map(alarmZeile).join('')+'</ul>';
 return '<div class="konto-block"><h3 class="konto-h">'+ka('alarme')+'</h3>'+inhalt+'<button type="button" class="konto-knopf-neben" data-konto="alarm-neu">'+ka('alarmNeu')+'</button></div>';
}
function zeileKnopf(aktion,titel,text,klasse){return '<li><button type="button" class="konto-zeile'+(klasse?' '+klasse:'')+'" data-konto="'+aktion+'"><span class="konto-zeile-text"><b>'+titel+'</b>'+(text?'<small>'+text+'</small>':'')+'</span>'+pfeil+'</button></li>'}
function htmlAn(){
 const n=zustand.nutzer||{},mail=n.email||(IT.emailVonSitzung&&IT.emailVonSitzung())||'';
 const k=zustand.konto,abo=k&&(k.premium||k.paywall);
 return '<div class="konto-kopf"><span class="eyebrow konto-eyebrow">'+ka('eyebrow')+'</span><h2 id="konto-ansicht-titel" tabindex="-1">'+ka('titel')+'</h2></div>'
  +'<dl class="konto-fakten"><div><dt>'+ka('email')+'</dt><dd>'+esc(mail)+'</dd></div><div><dt>'+ka('seit')+'</dt><dd>'+(n.created_at?esc(datumLang(n.created_at)):'—')+'</dd></div></dl>'
  +alarmBlock()+sprachwahl()
  +(IT.installierbar&&IT.installierbar()?'<div class="konto-block"><h3 class="konto-h">'+ka('installTitel')+'</h3><ul class="konto-liste">'+zeileKnopf('install',ka('install'),ka('installText'))+'</ul></div>':'')
  +(abo?'<div class="konto-block"><h3 class="konto-h">'+ka('abo')+'</h3><ul class="konto-liste">'+zeileKnopf('abo',t('kontoMenueAbo'),'')+'</ul></div>':'')
  +'<div class="konto-block"><h3 class="konto-h">'+ka('mein')+'</h3><ul class="konto-liste">'
  +'<li><details class="konto-details"'+(zustand.offen==='email'?' open':'')+'><summary class="konto-zeile"><span class="konto-zeile-text"><b>'+ka('emailAendern')+'</b></span>'+pfeil+'</summary>'
  +'<form id="konto-email-form" class="konto-form" novalidate><label for="konto-email-neu">'+ka('emailNeu')+'</label><input id="konto-email-neu" type="email" autocomplete="email" inputmode="email" maxlength="200" required>'
  +'<p id="konto-email-meldung" class="'+(zustand.meldungOk?'ok':'access-error')+'" role="status">'+esc(zustand.meldung)+'</p><button type="submit" class="primary full">'+ka('emailSpeichern')+'</button></form></details></li>'
  +zeileKnopf('passwort',ka('passwort'),'')
  +zeileKnopf('export',ka('export'),ka('exportText'))
  +zeileKnopf('ueberall',ka('ueberall'),ka('ueberallText'))
  +zeileKnopf('loeschen',ka('loeschen'),'','konto-gefahr')+'</ul></div>'
  +'<button type="button" class="konto-abmelden" data-konto="abmelden">'+ka('abmelden')+'</button>'+fuss();
}
function htmlAus(){
 return '<div class="konto-kopf"><span class="eyebrow konto-eyebrow">'+ka('eyebrow')+'</span><h2 id="konto-ansicht-titel" tabindex="-1">'+ka('titelAus')+'</h2><p class="konto-aus-satz">'+ka('ausSatz')+'</p>'
  +'<button type="button" class="primary konto-anmelden" data-konto="anmelden">'+ka('anmelden')+'</button></div>'+sprachwahl()+fuss();
}
function zeichne(){
 if(sicht.hidden)return;
 const fokusId=document.activeElement&&sicht.contains(document.activeElement)&&document.activeElement.id;
 const offen=sicht.querySelector('.konto-details[open]');zustand.offen=offen?'email':zustand.offen;
 const getippt=sicht.querySelector('#konto-email-neu')?.value||'';
 sicht.innerHTML='<div class="konto-innen">'+(angemeldet()?htmlAn():htmlAus())+'</div>';
 const e=sicht.querySelector('#konto-email-neu');if(e)e.value=getippt;
 if(fokusId)sicht.querySelector('#'+fokusId)?.focus({preventScroll:true});
}
async function laden(){
 if(!angemeldet()||zustand.laedt)return;zustand.laedt=true;
 const tok=await IT.token().catch(()=>null);
 if(!tok){zustand.laedt=false;return}
 const [n,a,k]=await Promise.all([
  fetch(IT.authUrl+'/auth/v1/user',{headers:{apikey:IT.authKey,Authorization:'Bearer '+tok}}).then(r=>r.ok?r.json():null).catch(()=>null),
  api('alarme').catch(()=>({fehler:true})),api('konto').catch(()=>null)]);
 zustand.nutzer=n;zustand.alarme=a;zustand.konto=k;zustand.laedt=false;zeichne();
}
IT.kontoNeuLaden=()=>{if(!sicht.hidden){zustand.alarme=null;laden()}};
async function emailAendern(form){
 const i=form.querySelector('#konto-email-neu'),neu=i.value.trim(),knopf=form.querySelector('button[type=submit]');
 const melde=(text,ok)=>{zustand.meldung=text;zustand.meldungOk=!!ok;const m=sicht.querySelector('#konto-email-meldung');if(m){m.textContent=text;m.className=ok?'ok':'access-error'}};
 if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(neu)){melde(t('emailInvalid'));i.focus();return}
 if(neu.toLowerCase()===String((zustand.nutzer||{}).email||IT.emailVonSitzung()).toLowerCase()){melde(ka('emailGleich'));return}
 knopf.disabled=true;
 try{const tok=await IT.token();if(!tok)throw 'login';
  const r=await fetch(IT.authUrl+'/auth/v1/user?redirect_to='+encodeURIComponent(location.origin+'/#konto'),{method:'PUT',headers:{apikey:IT.authKey,'Content-Type':'application/json',Authorization:'Bearer '+tok},body:JSON.stringify({email:neu})});
  if(!r.ok){const d=await r.json().catch(()=>({}));throw d.error_code||d.code||r.status}
  melde(ka('emailGesendet'),true);i.value='';
 }catch(c){melde(c==='email_exists'||c===422?ka('emailVergeben'):c===429||c==='over_email_send_rate_limit'?t('linkRate'):ka('fehler'))}
 knopf.disabled=false;
}
async function exportieren(b){
 b.disabled=true;
 try{const d=await api('konto/export');const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='investtimer-daten.json';document.body.append(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},1000);
 }catch{typeof toast==='function'&&toast(ka('fehler'))}
 b.disabled=false;
}
async function ueberallAbmelden(b){
 b.disabled=true;const tok=await IT.token().catch(()=>null);
 if(tok)await fetch(IT.authUrl+'/auth/v1/logout?scope=global',{method:'POST',headers:{apikey:IT.authKey,Authorization:'Bearer '+tok}}).catch(()=>{});
 IT.abmelden();
}
sicht.addEventListener('click',e=>{
 const b=e.target.closest('[data-konto]');if(!b)return;const a=b.dataset.konto;
 if(a==='anmelden')$('#account-login')?.click();
 else if(a==='alarme'||a==='alarm-neu')IT.oeffneAlarme&&IT.oeffneAlarme(b);
 else if(a==='install')IT.oeffneInstall&&IT.oeffneInstall(b);
 else if(a==='abo')IT.oeffneKonto&&IT.oeffneKonto(b,IT.aboAnsicht?IT.aboAnsicht():'konto');
 else if(a==='passwort'||a==='loeschen'){IT.oeffneKonto&&IT.oeffneKonto(b,'konto').then(()=>{const d=$(a==='passwort'?'.konto-pw':'.konto-loeschen');if(d){d.open=true;d.scrollIntoView({block:'nearest'});d.querySelector('input')?.focus({preventScroll:true})}})}
 else if(a==='export')exportieren(b);
 else if(a==='ueberall')ueberallAbmelden(b);
 else if(a==='abmelden'){IT.abmelden();setTimeout(()=>$('#konto-ansicht-titel')?.focus({preventScroll:true}),0)}
});
sicht.addEventListener('submit',e=>{if(e.target.id==='konto-email-form'){e.preventDefault();emailAendern(e.target)}});
sicht.addEventListener('toggle',e=>{if(e.target.classList&&e.target.classList.contains('konto-details'))zustand.offen=e.target.open?'email':''},true);
sicht.addEventListener('change',e=>{if(e.target.id!=='konto-sprache')return;const h=$('#header-language');if(h){h.value=e.target.value;h.dispatchEvent(new Event('change',{bubbles:true}))}});
/* Alarm-Dialog geschlossen: Liste neu laden */
document.addEventListener('close',e=>{if(e.target&&e.target.id==='alarm-dialog')IT.kontoNeuLaden()},true);
IT.kontoAnsicht={zeigen(){sicht.hidden=false;zeichne();laden()},verbergen(){sicht.hidden=true},element:sicht};
document.addEventListener('investtimer:update',()=>{if(!angemeldet()){zustand.nutzer=null;zustand.alarme=null;zustand.konto=null}if(!sicht.hidden){zeichne();laden()}});
new MutationObserver(()=>zeichne()).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
})();
