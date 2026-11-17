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

--anmeldung=<datei>: echte Anmeldung per E-Mail-Link (Supabase-Projekt von
InvestTimer; Datei mit {"url": ..., "anonKey": ...}, beides oeffentlich). Dann
  - oeffentlich nur der zeitversetzte Stand, der aktuelle Wert kommt mit
    Login-Token ueber /api/aktuell, die KI verlangt das Token ebenfalls
  - der Entwurfs-Umschalter "Oeffentlich / Nach Login" entfaellt

Immer: Halbmond-Fuellung des Signalbogens, Halbmond als Zeichen der KI und als
Denk-Anzeige, Web-App-Manifest.
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
from build_public import GAUGE_CSS, GAUGE_JS, MOBILE_CSS, once, sub_once  # noqa: E402

# Halbmond: Zeichen der KI (gefuellt bis zum angezeigten Wert) und Denk-Anzeige
MOND = ('<svg class="{cls}" viewBox="3 13 42 24" aria-hidden="true">'
        '<path class="mond-spur" d="M6 34a18 18 0 0 1 36 0" pathLength="100"/>'
        '<path class="mond-wert" d="M6 34a18 18 0 0 1 36 0" pathLength="100"/></svg>')

HALBMOND_CSS = """
/* Halbmond als Zeichen der KI und als Denk-Anzeige */
.ki-halbmond{overflow:visible}
.ki-halbmond path{fill:none;stroke-width:4.2;stroke-linecap:round}
.ki-halbmond .mond-spur{stroke:#d3dccf}
.ki-halbmond .mond-wert{stroke:var(--accent);stroke-dasharray:var(--value,0) 100;transition:stroke-dasharray .9s cubic-bezier(.16,1,.3,1)}
.chat-wait .ki-halbmond{width:24px;height:14px;flex:none}
.chat-wait .ki-halbmond .mond-wert{stroke-dasharray:22 100;transition:none;animation:ki-denkt 1.5s cubic-bezier(.65,0,.35,1) infinite alternate}
@keyframes ki-denkt{from{stroke-dashoffset:0}to{stroke-dashoffset:-78}}
@media(prefers-reduced-motion:reduce){.chat-wait .ki-halbmond .mond-wert{animation:none;stroke-dasharray:var(--value,0) 100}.ki-halbmond .mond-wert{transition:none}}
"""

ANMELDUNG_CSS = """
/* Anmeldung per E-Mail-Link */
.access-form{display:grid;gap:8px;margin:20px 0 4px;text-align:left}
.access-form label{font-size:12px;color:var(--sub)}
.access-form input{min-height:48px;font-size:16px;padding:0 14px;border:1px solid #b9c7b6;border-radius:12px;background:var(--surface);color:var(--text);font-family:inherit}
.access-form input:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
.access-form button:disabled{opacity:.55}
.access-error{min-height:1.2em;margin:0;font-size:12px;line-height:1.5;color:#9b3d32}
.access-error.ok{color:var(--accent)}
.access-form .code-input{font-size:24px;letter-spacing:.42em;text-align:center;font-variant-numeric:tabular-nums;padding-left:.42em}
.access-form .code-input::placeholder{color:#c9d3c6}
.access-form button[type=submit]{min-height:48px}
.access-more{display:flex;justify-content:space-between;gap:12px;margin:14px 0 0}
.text-button{min-height:44px;padding:0 4px;border:0;background:none;color:var(--accent);font:inherit;font-size:13px;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.text-button:disabled{color:var(--sub);text-decoration:none;cursor:default}
.access-dialog{overscroll-behavior:contain}
.access-dialog .preview-notice a{color:inherit}
@media(max-width:760px){.access-dialog{max-height:calc(100dvh - 12px);overflow-y:auto}.access-benefits{margin-bottom:4px}}
.rechtliches{font-size:12px;color:var(--sub)}.rechtliches a{color:inherit;display:inline-block;padding:12px 2px}
/* Alarme, Push, Installation */
#saved-alerts{display:none}
/* Angemeldet: Einstieg zu den Alarmen direkt unter dem Wert (im Entwurf nur tief in den Details) */
.members-layout .score-column .subscribe-module{display:block;margin-top:18px}
.push-box{margin:18px 0;padding:14px 16px;border:1px solid var(--line);border-radius:14px;background:var(--panel);font-size:14px;line-height:1.6}
.push-box p{margin:0 0 8px;color:var(--text)}.push-box p:last-child{margin-bottom:0}.push-box .primary{margin-top:6px}.push-box .access-more{margin:4px 0 0}
.alarm-liste{list-style:none;margin:6px 0 14px;padding:0;display:grid;gap:8px}
.alarm-eintrag{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.alarm-eintrag.pausiert .alarm-text{opacity:.6}
.alarm-text{flex:1;display:grid;gap:2px}.alarm-text b{font-size:15px;font-weight:500}.alarm-text small{font-size:12px;color:var(--sub)}
.alarm-schalter{position:relative;display:inline-flex;align-items:center;min-height:44px;flex:none;cursor:pointer}
.alarm-schalter input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:pointer}
.alarm-schalter .spur{position:relative;display:block;width:46px;height:28px;border-radius:14px;background:#cfd8cc;transition:background .2s}
.alarm-schalter .spur::after{content:"";position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.2);transition:transform .2s}
.alarm-schalter input:checked+.spur{background:var(--accent)}.alarm-schalter input:checked+.spur::after{transform:translateX(18px)}
.alarm-schalter input:focus-visible+.spur{outline:2px solid var(--accent);outline-offset:2px}
.alarm-leer{font-size:14px;color:var(--sub);margin:6px 0 14px}
.alarm-form select{min-height:48px;font-size:16px;padding:0 12px;border:1px solid #b9c7b6;border-radius:12px;background:var(--surface);color:var(--text);font-family:inherit}
.alarm-schwelle{display:flex;justify-content:space-between;align-items:baseline;margin-top:8px}
.alarm-schwelle output{font-size:28px;font-variant-numeric:tabular-nums;color:var(--text)}
.alarm-form input[type=range]{width:100%;min-height:44px;accent-color:var(--accent)}
.install-schritte{margin:8px 0 0;padding-left:22px;display:grid;gap:8px;font-size:14px;line-height:1.55}
.install-schritte .teilen{width:18px;height:18px;vertical-align:-3px;color:var(--accent)}
.install-link{font-size:12px;color:var(--sub);min-height:44px}
@media(prefers-reduced-motion:reduce){.alarm-schalter .spur,.alarm-schalter .spur::after{transition:none}}
/* Ohne Impressum und Datenschutzerklaerung: kein Einstieg in Registrierung oder Anmeldung */
body.ohne-registrierung:not(.members-layout) #open-subscribe,
body.ohne-registrierung:not(.members-layout) .public-access-note,
body.ohne-registrierung:not(.members-layout) #account-login,
body.ohne-registrierung:not(.members-layout) .benefit-line{display:none}
"""

# Alarme, Push und Installation (tools/alarme.js)
ALARM_JS = (ROOT / "tools" / "alarme.js").read_text(encoding="utf-8")
TEXTE_ALARM_DE = ("alarmEyebrow:'DEINE ALARME',alarmTitle:'Deine Schwelle. Dein Hinweis.',"
                  "alarmIntro:'Lege fest, bei welchem Marktstress du eine Nachricht aufs Handy bekommst.',"
                  "alarmWenn:'Benachrichtigen, wenn der Marktstress',alarmSteigt:'über die Schwelle steigt',alarmFaellt:'unter die Schwelle fällt',"
                  "alarmSchwelle:'Schwelle',alarmSpeichern:'Alarm speichern',alarmUeber:'Steigt über',alarmUnter:'Fällt unter',"
                  "alarmAktiv:'aktiv',alarmPausiert:'pausiert',alarmLoeschen:'Löschen',alarmKeine:'Noch kein Alarm angelegt.',"
                  "alarmLaedt:'Wird geladen …',alarmFehler:'Das hat nicht geklappt. Bitte versuche es gleich noch einmal.',"
                  "alarmDoppelt:'Diesen Alarm gibt es schon.',alarmMax:'Du kannst bis zu fünf Alarme anlegen.',"
                  "alarmRegel:'Ein Alarm meldet sich, wenn der Wert die Schwelle überschreitet, höchstens einmal am Tag. Der Hinweis beschreibt nur den Stand und ist keine Anlageberatung.',"
                  "pushAktiv:'Push ist auf diesem Gerät eingeschaltet.',pushTest:'Testnachricht senden',pushTestGesendet:'Testnachricht ist unterwegs',"
                  "pushTestWarten:'Bitte eine Minute warten',pushAus:'Push ausschalten',"
                  "pushAusText:'Damit dich ein Alarm erreicht, schalte Mitteilungen auf diesem Gerät ein.',pushAn:'Mitteilungen einschalten',"
                  "pushBlockiert:'Mitteilungen sind für InvestTimer blockiert. Erlaube sie in den Einstellungen deines Geräts oder Browsers, dann klappt es.',"
                  "pushNein:'Dieser Browser kann keine Mitteilungen empfangen. Nutze ein aktuelles Chrome, Edge, Firefox oder Safari.',"
                  "iosTitel:'Auf dem iPhone kommen Mitteilungen nur in der installierten App an:',"
                  "ios1:'Tippe in Safari unten auf Teilen {teilen}.',ios2:'Wähle „Zum Home-Bildschirm“ und tippe auf „Hinzufügen“.',"
                  "ios3:'Öffne InvestTimer vom Home-Bildschirm und melde dich dort mit dem Code aus der E-Mail an.',"
                  "installLink:'App installieren',installTitel:'InvestTimer als App',"
                  "installIOS:'Ohne App Store, in drei Schritten (iPhone und iPad ab iOS 16.4):',"
                  "installAndroid:'InvestTimer lässt sich direkt installieren und startet dann wie eine App.',installJetzt:'Jetzt installieren',"
                  "installAndere:'In Chrome oder Edge: Menü ⋮ öffnen und „App installieren“ oder „Zum Startbildschirm hinzufügen“ wählen. In Safari auf dem Mac: Ablage → „Zum Dock hinzufügen“.',"
                  "installPush:'In der App kannst du Alarme mit Push-Mitteilung einrichten.',")
TEXTE_ALARM_EN = ("alarmEyebrow:'YOUR ALERTS',alarmTitle:'Your threshold. Your alert.',"
                  "alarmIntro:'Choose at which market stress level you get a notification.',"
                  "alarmWenn:'Notify me when market stress',alarmSteigt:'rises above the threshold',alarmFaellt:'falls below the threshold',"
                  "alarmSchwelle:'Threshold',alarmSpeichern:'Save alert',alarmUeber:'Rises above',alarmUnter:'Falls below',"
                  "alarmAktiv:'active',alarmPausiert:'paused',alarmLoeschen:'Delete',alarmKeine:'No alerts yet.',"
                  "alarmLaedt:'Loading …',alarmFehler:'That did not work. Please try again in a moment.',"
                  "alarmDoppelt:'This alert already exists.',alarmMax:'You can create up to five alerts.',"
                  "alarmRegel:'An alert fires when the score crosses the threshold, at most once a day. It only describes the reading and is not investment advice.',"
                  "pushAktiv:'Push is on for this device.',pushTest:'Send test notification',pushTestGesendet:'Test notification is on its way',"
                  "pushTestWarten:'Please wait a minute',pushAus:'Turn off push',"
                  "pushAusText:'Turn on notifications on this device so alerts can reach you.',pushAn:'Turn on notifications',"
                  "pushBlockiert:'Notifications are blocked for InvestTimer. Allow them in your device or browser settings.',"
                  "pushNein:'This browser cannot receive notifications. Use a current Chrome, Edge, Firefox or Safari.',"
                  "iosTitel:'On iPhone, notifications only arrive in the installed app:',"
                  "ios1:'In Safari, tap Share {teilen} at the bottom.',ios2:'Choose “Add to Home Screen” and tap “Add”.',"
                  "ios3:'Open InvestTimer from your Home Screen and sign in there with the code from the email.',"
                  "installLink:'Install app',installTitel:'InvestTimer as an app',"
                  "installIOS:'No App Store needed, three steps (iPhone and iPad with iOS 16.4 or later):',"
                  "installAndroid:'InvestTimer can be installed directly and then starts like an app.',installJetzt:'Install now',"
                  "installAndere:'In Chrome or Edge: open the menu ⋮ and choose “Install app” or “Add to Home screen”. In Safari on Mac: File → “Add to Dock”.',"
                  "installPush:'In the app you can set up alerts with push notifications.',")

TEXTE_ANMELDUNG_DE = ("email:'E-Mail-Adresse',emailPlaceholder:'name@beispiel.de',sendLink:'Anmeldelink senden',sending:'Wird gesendet …',"
                      "linkSentTitle:'Schau in dein Postfach.',"
                      "linkSent:'Wir haben dir an {email} einen Anmeldelink und einen sechsstelligen Code geschickt. Tippe auf den Link oder gib den Code hier ein.',"
                      "linkSentLink:'Wir haben dir an {email} einen Anmeldelink geschickt. Ein Tipp darauf, und du siehst den aktuellen Marktstress. Öffne den Link am besten auf diesem Gerät.',"
                      "code:'Code aus der E-Mail',codeSubmit:'Anmelden',checking:'Wird geprüft …',"
                      "codeInvalid:'Der Code stimmt nicht oder ist abgelaufen. Prüfe ihn oder fordere einen neuen an.',"
                      "codeShort:'Bitte gib die sechs Ziffern aus der E-Mail ein.',"
                      "resend:'Neu senden',resendIn:'Neu senden in {s} s',resent:'Neue E-Mail ist unterwegs.',otherEmail:'Andere Adresse',"
                      "spamHint:'Keine E-Mail da? Sieh im Spam-Ordner nach. Die Zustellung kann eine Minute dauern.',"
                      "emailInvalid:'Bitte gib eine gültige E-Mail-Adresse ein.',"
                      "linkRate:'Gerade wurden zu viele Links angefordert. Bitte versuche es in ein paar Minuten erneut.',"
                      "linkFail:'Der Link konnte nicht verschickt werden. Bitte versuche es gleich noch einmal.',"
                      "linkExpired:'Der Anmeldelink ist abgelaufen oder wurde schon benutzt. Fordere einfach einen neuen an.',"
                      "accessLegal:'Kein Passwort nötig: Du bekommst einen Anmeldelink per E-Mail. Neu hier? Damit wird dein Zugang angelegt.',"
                      "legalLinks:'Mit der Anmeldung gilt unsere <a href=\\\"/datenschutz.html\\\">Datenschutzerklärung</a>.',"
                      "loginNeeded:'Bitte melde dich erneut an, um weiter zu fragen.',"
                      + TEXTE_ALARM_DE)
TEXTE_ANMELDUNG_EN = ("email:'Email address',emailPlaceholder:'name@example.com',sendLink:'Send sign-in link',sending:'Sending …',"
                      "linkSentTitle:'Check your inbox.',"
                      "linkSent:'We sent a sign-in link and a six-digit code to {email}. Tap the link or enter the code here.',"
                      "linkSentLink:'We sent a sign-in link to {email}. One tap and you will see the latest market stress. Best open it on this device.',"
                      "code:'Code from the email',codeSubmit:'Sign in',checking:'Checking …',"
                      "codeInvalid:'The code is wrong or has expired. Check it or request a new one.',"
                      "codeShort:'Please enter the six digits from the email.',"
                      "resend:'Resend',resendIn:'Resend in {s} s',resent:'A new email is on its way.',otherEmail:'Different address',"
                      "spamHint:'No email? Check your spam folder. Delivery can take a minute.',"
                      "emailInvalid:'Please enter a valid email address.',"
                      "linkRate:'Too many links were requested just now. Please try again in a few minutes.',"
                      "linkFail:'The link could not be sent. Please try again in a moment.',"
                      "linkExpired:'The sign-in link has expired or was already used. Simply request a new one.',"
                      "accessLegal:'No password needed: we email you a sign-in link. New here? That creates your access.',"
                      "legalLinks:'Signing in is subject to our <a href=\\\"/datenschutz.html\\\">privacy policy</a>.',"
                      "loginNeeded:'Please sign in again to keep asking.',"
                      + TEXTE_ALARM_EN)

# Ersetzt LIVE_JS, wenn die Anmeldung aktiv ist. Sitzung im localStorage, Erneuerung ueber das Refresh-Token.
LIVE_JS_ANMELDUNG = """/* Oeffentlich: zeitversetzter Stand aus /data/stress.json. Aktuell: nur nach Anmeldung ueber /api/aktuell. */
const IT=window.InvestTimer={live:null,pub:result,member:false,chat:null,session:null,
 get view(){return this.member&&this.live?this.live:this.pub},
 setMember(v){this.member=!!v;apply()}};
function apply(){
 const open=$$('#details-panel details').map(e=>e.open),y=window.scrollY;
 result=IT.view;render();
 $$('#details-panel details').forEach((e,i)=>{e.open=!!open[i]});window.scrollTo(0,y);
 document.dispatchEvent(new Event('investtimer:update'));
}
const AUTH=__AUTH__,SKEY='investtimer-sitzung';
const merke=s=>{try{s?localStorage.setItem(SKEY,JSON.stringify(s)):localStorage.removeItem(SKEY)}catch{}};
const gemerkt=()=>{try{return JSON.parse(localStorage.getItem(SKEY)||'null')}catch{return null}};
const sb=(pfad,opt={})=>fetch(AUTH.url+pfad,{...opt,headers:{apikey:AUTH.key,'Content-Type':'application/json',...(opt.headers||{})}});
(()=>{/* Rueckkehr aus dem E-Mail-Link: Sitzung uebernehmen, Adresse bereinigen */
 const h=new URLSearchParams(location.hash.slice(1));if(!h.has('access_token')&&!h.has('error'))return;
 if(h.get('access_token'))merke({access_token:h.get('access_token'),refresh_token:h.get('refresh_token'),
  expires_at:Number(h.get('expires_at'))||Math.floor(Date.now()/1000)+Number(h.get('expires_in')||3600)});
 else IT.anmeldeFehler=h.get('error_description')||h.get('error');
 history.replaceState(null,'',location.pathname+location.search);
})();
let erneuern=null;
IT.token=async()=>{
 let s=IT.session||gemerkt();if(!s||!s.access_token)return null;
 if(Date.now()/1000>(s.expires_at||0)-60){
  erneuern=erneuern||sb('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:JSON.stringify({refresh_token:s.refresh_token})})
   .then(r=>r.ok?r.json():Promise.reject(r.status)).finally(()=>{erneuern=null});
  try{const d=await erneuern;s={access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Math.floor(Date.now()/1000)+(d.expires_in||3600)};merke(s)}
  catch(e){if(e===400||e===401){merke(null);IT.session=null}return null}
 }
 IT.session=s;return s.access_token;
};
IT.sendeLink=async email=>{
 const r=await sb('/auth/v1/otp?redirect_to='+encodeURIComponent(location.origin+'/'),{method:'POST',body:JSON.stringify({email,create_user:true})});
 if(!r.ok)throw r.status;
};
IT.pruefeCode=async(email,code)=>{
 const r=await sb('/auth/v1/verify',{method:'POST',body:JSON.stringify({type:'email',email,token:code})});
 if(!r.ok)throw r.status;const d=await r.json();
 const s={access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Math.floor(Date.now()/1000)+(d.expires_in||3600)};
 merke(s);IT.session=s;IT.member=true;loadLive(true);
};
IT.abmelden=async()=>{
 const s=IT.session||gemerkt();merke(null);IT.session=null;IT.live=null;IT.setMember(false);
 if(s)sb('/auth/v1/logout',{method:'POST',headers:{Authorization:'Bearer '+s.access_token}}).catch(()=>{});
};
let lastLoad=0,lastSeen='';
function loadLive(force){
 if(!location.protocol.startsWith('http')||(!force&&Date.now()-lastLoad<3e5))return;lastLoad=Date.now();
 document.body.dataset.live='laedt';
 const oeffentlich=fetch('/data/stress.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject())
  .then(d=>normaliseResult(d.publicSnapshot)||normaliseResult(d)).catch(()=>null);
 const aktuell=IT.token().then(tok=>!tok?null:fetch('/api/aktuell',{cache:'no-store',headers:{Authorization:'Bearer '+tok}})
  .then(r=>{if(r.status===401){IT.abmelden();return null}return r.ok?r.json():null}).then(d=>d&&normaliseResult(d))).catch(()=>null);
 Promise.all([oeffentlich,aktuell]).then(([pub,live])=>{
  document.body.dataset.live='fertig';
  if(!pub&&!live){lastLoad=0;return}
  const seen=JSON.stringify([live,pub,!!IT.session]);if(seen===lastSeen)return;
  if(document.querySelector('dialog[open]:not(#access-preview-dialog)')){lastLoad=0;return}
  if(pub)IT.pub=pub;IT.live=live;lastSeen=seen;IT.member=!!(live&&IT.session);apply();
 });
}
IT.loadLive=loadLive;
if(gemerkt())IT.member=true;
loadLive();
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')loadLive()});
window.addEventListener('pageshow',e=>{if(e.persisted)loadLive()});
if(location.protocol.startsWith('http'))fetch('/api/chat',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{IT.chat=!!(d&&d.ok)}).catch(()=>{IT.chat=false});
"""

# Anmeldedialog: E-Mail-Adresse -> Anmeldelink (ersetzt den Knopf "Mitgliederansicht ansehen")
ZUGANG_JS_ANMELDUNG = """let gesendet='',zugangsFehler='',sperreBis=0,uhr=null;
const warte=()=>Math.max(0,Math.ceil((sperreBis-Date.now())/1000));
function neuKnopf(){const k=$('#access-resend');if(!k)return;const s=warte();k.disabled=s>0;k.textContent=s?t('resendIn').replace('{s}',s):t('resend');if(!s){clearInterval(uhr);uhr=null}}
function renderAccess(){
 const kopf='<div class="modal-top"><span class="eyebrow">INVESTTIMER</span><button class="close-button" id="close-access" type="button" aria-label="'+t('close')+'">×</button></div>';
 const recht=REGISTRIERUNG_RECHT?'<p class="preview-notice">'+t('accessLegal')+' '+t('legalLinks')+'</p>':'<p class="preview-notice">'+t('accessLegal')+'</p>';
 access.innerHTML=kopf+(gesendet
  ?'<h2 id="access-title" tabindex="-1">'+t('linkSentTitle')+'</h2><p>'+esc(t(CODE_AKTIV?'linkSent':'linkSentLink')).replace('{email}','<b>'+esc(gesendet)+'</b>')+'</p>'
   +(CODE_AKTIV?'<form id="code-form" class="access-form" novalidate><label for="access-code">'+t('code')+'</label>'
   +'<input id="access-code" class="code-input" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]*" maxlength="6" placeholder="000000" required>'
   +'<p class="access-error" id="access-error" role="alert"></p><button class="primary full" type="submit">'+t('codeSubmit')+'</button></form>'
    :'<p class="access-error" id="access-error" role="alert"></p>')
   +'<div class="access-more"><button type="button" class="text-button" id="access-resend"></button><button type="button" class="text-button" id="access-other">'+t('otherEmail')+'</button></div>'
   +'<p class="preview-notice">'+t('spamHint')+'</p>'
  :'<h2 id="access-title" tabindex="-1">'+t('accessTitle')+'</h2><p>'+t('accessIntro')+'</p><ul class="access-benefits"><li>'+t('feature1')+'</li><li>'+t('feature2')+'</li><li>'+t('feature3')+'</li></ul>'
   +'<form id="access-form" class="access-form" novalidate><label for="access-email">'+t('email')+'</label>'
   +'<input id="access-email" type="email" inputmode="email" autocomplete="email" autocapitalize="off" spellcheck="false" enterkeyhint="send" maxlength="254" required placeholder="'+t('emailPlaceholder')+'">'
   +'<p class="access-error" id="access-error" role="alert">'+esc(zugangsFehler)+'</p><button class="primary full" type="submit">'+t('sendLink')+'</button></form>'
   +recht);
 if(gesendet){neuKnopf();if(warte()&&!uhr)uhr=setInterval(neuKnopf,1000)}
}
async function sende(email,fehler,knopf,text){
 knopf.disabled=true;const alt=knopf.textContent;if(text)knopf.textContent=text;
 try{await IT.sendeLink(email);sperreBis=Date.now()+60000;return true}
 catch(s){fehler.textContent=t(s===429?'linkRate':'linkFail');if(s===429)sperreBis=Date.now()+60000;return false}
 finally{knopf.textContent=alt;knopf.disabled=false}
}
document.addEventListener('click',async e=>{
 if(e.target.closest('#access-done'))closeAccess();
 else if(e.target.closest('#access-other')){gesendet='';renderAccess();$('#access-email').focus()}
 else if(e.target.closest('#access-resend')){const f=$('#access-error');f.textContent='';
  f.classList.remove('ok');if(await sende(gesendet,f,e.target.closest('button'),t('sending'))){f.textContent=t('resent');f.classList.add('ok')}
  neuKnopf();if(!uhr&&warte())uhr=setInterval(neuKnopf,1000)}
});
document.addEventListener('input',e=>{if(e.target.id!=='access-code')return;const v=e.target.value.replace(/\\D/g,'').slice(0,6);e.target.value=v;
 if(v.length===6)e.target.form.requestSubmit()});
document.addEventListener('submit',async e=>{
 if(e.target.id==='code-form'){e.preventDefault();
  const input=$('#access-code'),fehler=$('#access-error'),knopf=e.target.querySelector('button'),code=input.value.trim();
  fehler.classList.remove('ok');if(!/^\\d{6}$/.test(code)){fehler.textContent=t('codeShort');input.focus();return}
  if(knopf.disabled)return;knopf.disabled=true;knopf.textContent=t('checking');fehler.textContent='';
  try{await IT.pruefeCode(gesendet,code);gesendet='';closeAccess()}
  catch(s){fehler.textContent=t(s===429?'linkRate':'codeInvalid');knopf.disabled=false;knopf.textContent=t('codeSubmit');input.select()}
  return}
 if(e.target.id!=='access-form')return;e.preventDefault();
 const input=$('#access-email'),fehler=$('#access-error'),knopf=e.target.querySelector('button'),email=input.value.trim().toLowerCase();
 if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$/.test(email)){fehler.textContent=t('emailInvalid');input.focus();return}
 fehler.textContent='';zugangsFehler='';
 if(await sende(email,fehler,knopf,t('sending'))){gesendet=email;renderAccess();$('#access-title').focus({preventScroll:true})}
});
"""

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
function turnMarkup(turn){return '<div class="chat-bubble chat-question">'+esc(turn.text)+'</div><div class="chat-bubble chat-answer">'+(turn.answer===null?'<span class="chat-wait" role="status">__MOND_DENKT__'+t('thinking')+'</span>':md(turn.answer))+'</div>'}
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
  const tok=IT.token?await IT.token():null;
  const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json',...(tok?{Authorization:'Bearer '+tok}:{})},body:JSON.stringify({frage:text,verlauf})});
  if(res.status===401){answer=t('loginNeeded');IT.abmelden&&IT.abmelden()}else if(res.status===429)answer=t('limit');else if(!res.ok)throw new Error('HTTP '+res.status);else answer=String((await res.json()).antwort||'');
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
             '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
             '<link rel="manifest" href="/manifest.json">',
             '<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">'
             '<meta name="apple-mobile-web-app-status-bar-style" content="default">']
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


def rechtsseiten(target):
    """Registrierung erst, wenn Impressum und Datenschutzerklaerung ausgeliefert werden."""
    return all((Path(target) / n).is_file() for n in ("impressum.html", "datenschutz.html"))


def main(source, target_dir, preview, anmeldung=None):
    html = Path(source).read_text(encoding="utf-8")
    if anmeldung and not (str(anmeldung.get("url", "")).startswith("https://") and anmeldung.get("anonKey")):
        raise SystemExit("Anmeldedatei braucht url (https://...) und anonKey")
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
    html = once(html, "connect-src 'none'", "connect-src 'self'%s; manifest-src 'self'; worker-src 'self'" % (
        " " + anmeldung["url"].rstrip("/") if anmeldung else ""), "CSP Abrufe")
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
    live_js = LIVE_JS
    if anmeldung:
        live_js = LIVE_JS_ANMELDUNG.replace("__AUTH__", json.dumps(
            {"url": anmeldung["url"].rstrip("/"), "key": anmeldung["anonKey"]}))
    html = once(html, "render();\n\n})();\n(() => {\n/* 04 ·", "render();\n" + live_js + "\n})();\n(() => {\n/* 04 ·", "Live-Abruf")

    # Signalbogen: Halbmond fuellt sich (gleicher Baustein wie in build_public.py)
    html = sub_once(html, r"function updateGauge\(\)\{.*?\n\}\nfunction renderModule\(\)\{",
                    GAUGE_JS + "function renderModule(){", "updateGauge")
    html = once(html, "new MutationObserver(updateGauge).observe(score,",
                "gaugeObserver=new MutationObserver(updateGauge);gaugeObserver.observe(score,", "Gauge-Observer")

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
    html = once(html, "const c={de:{login:'Anmelden',", "const c={de:{" + KEYS_DE + TEXTE_ANMELDUNG_DE + "login:'Anmelden',", "Texte de")
    html = once(html, "},en:{login:'Sign in',logout:'Sign out',preview:", "},en:{" + KEYS_EN + TEXTE_ANMELDUNG_EN + "login:'Sign in',logout:'Sign out',preview:", "Texte en")
    # KI-Zeichen: Halbmond statt Netz-Symbol
    html = sub_once(html, r"const orbit='<svg class=\"assistant-orbit\".*?</svg>';",
                    "const orbit='" + MOND.format(cls="assistant-orbit ki-halbmond") + "';", "KI-Zeichen")
    if anmeldung:
        html = once(html, "function update(){", "function update(){member=!!IT.member;", "Zugang folgt Anmeldung")
        html = once(html, "if(member&&b.id==='account-login')switchView(false);else openAccess(b);",
                    "if(member&&b.id==='account-login')IT.abmelden();else openAccess(b);", "Abmelden")
        html = once(html, "$('.app').after(review);", "/* Entwurfsansicht entfaellt mit echter Anmeldung */", "Entwurfsansicht")
        offen = rechtsseiten(target)
        html = sub_once(html, r"function renderAccess\(\)\{access\.innerHTML=[^\n]*\n",
                        ZUGANG_JS_ANMELDUNG.replace("REGISTRIERUNG_RECHT", "true" if offen else "false")
                        .replace("CODE_AKTIV", "true" if anmeldung.get("code", True) else "false"), "Anmeldedialog")
        if not offen:
            html = once(html, "<body>", '<body class="ohne-registrierung">', "Registrierung aus")
            html = once(html, "databodyPublic:'Historischer Wert vom {datelong}. Den aktuellen Marktstress siehst du nach der Anmeldung.'",
                        "databodyPublic:'Historischer Wert vom {datelong}.'", "databodyPublic de ohne Registrierung")
            html = once(html, "databodyPublic:'Historical reading from {datelong}. The latest market stress is available after sign-in.'",
                        "databodyPublic:'Historical reading from {datelong}.'", "databodyPublic en ohne Registrierung")
        else:
            html = once(html, '<span data-i18n="tagline">Marktstress verstehen.</span></footer>',
                        '<span data-i18n="tagline">Marktstress verstehen.</span>'
                        '<nav class="rechtliches"><a href="/impressum.html">Impressum</a> · <a href="/datenschutz.html">Datenschutz</a></nav></footer>',
                        "Fusslinks Rechtstexte")
        print("Registrierung: %s" % ("offen" if offen else "ausgeblendet (Impressum/Datenschutz fehlen)"))
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
                    CHAT_JS.replace("__FRAGEN__", json.dumps(kategorien, ensure_ascii=False)).replace("__MOND_DENKT__", MOND.format(cls="ki-halbmond")), "Chat-Kern")
    html = sub_once(html, r"document\.addEventListener\('submit',e=>\{if\(!\['assistant-entry-form'[^\n]*\n", SUBMIT_JS, "Chat-Absenden")
    html = once(html, "else if(b.dataset.ask)openChat(b.dataset.ask,null,b);",
                "else if(b.dataset.ask)openChat(t(b.dataset.ask==='composition'?'question2':'question1'),b);"
                "else if(b.dataset.more!==undefined)ask(b.dataset.more);"
                "else if(b.dataset.tab!==undefined){tab=Number(b.dataset.tab);renderChat(false);$('.assistant-messages').scrollTop=1e6}", "Chat-Klicks")
    html = once(html, "new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});\nupdate();",
                "new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});\n"
                "document.addEventListener('investtimer:update',update);\nupdate();" + (
                    "\nif(IT.anmeldeFehler){zugangsFehler=t('linkExpired');openAccess(null)}\n" + ALARM_JS
                    if anmeldung else ""), "Zugang Aktualisierung")

    # Stile: Mobil-Nachschaerfung hinter die Export-Stile, Ergaenzungen hinter die Zugangs-Stile
    head, rest = html.split('<style id="investtimer-access-style">', 1)
    head = once(head, "</style>", MOBILE_CSS + GAUGE_CSS + "</style>", "Mobil-CSS")
    access_css, rest = rest.split("</style>", 1)
    html = head + '<style id="investtimer-access-style">' + access_css + V12_CSS + HALBMOND_CSS + (ANMELDUNG_CSS if anmeldung else "") + "</style>" + rest

    for leftover in ("investtimer-snapshot", "evaluateSnapshot", "metricRows", "configRows", "Fear_Greed_Index",
                     "snapshotScore", "sourceLibraryFileId", "data:video", "answerKind", "BEISPIELANTWORT"):
        if leftover in html:
            raise SystemExit("Rest gefunden: " + leftover)
    (target / "index.html").write_text(html, encoding="utf-8")
    print("ok: oeffentlicher Rueckfall %s vom %s, %d Bytes HTML, Film %d Bytes" % (
        fallback["rounded"], fallback["asOf"], len(html.encode()), (target / "film" / "investtimer-49s.mp4").stat().st_size))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    datei = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--anmeldung=")), None)
    main(args[0], args[1], "--vorschau" in sys.argv, json.loads(Path(datei).read_text()) if datei else None)
