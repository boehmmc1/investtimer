/* Anmeldedialog: Passwort (Anmelden, Registrieren, Zuruecksetzen), E-Mail-Code als Zweitweg.
   Zustaende: anmelden | registrieren | bestaetigen (Code nach Registrierung) | vergessen | zuruecksetzen (Code + neues Passwort)
   | neu (neues Passwort nach Link) | code-email | code (Anmeldung per Code ohne Passwort) */
let modus='anmelden',gesendet='',zugangsFehler='',sperreBis=0,uhr=null,merkEmail='';
const warte=()=>Math.max(0,Math.ceil((sperreBis-Date.now())/1000));
const emailOk=e=>/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);
function neuKnopf(){const k=$('#access-resend');if(!k)return;const s=warte();k.disabled=s>0;k.textContent=s?t('resendIn').replace('{s}',s):t('resend');if(!s){clearInterval(uhr);uhr=null}}
const feldEmail=(auto)=>'<label for="access-email">'+t('email')+'</label><input id="access-email" type="email" inputmode="email" autocomplete="'+(auto||'email')+'" autocapitalize="off" spellcheck="false" maxlength="254" required placeholder="'+t('emailPlaceholder')+'" value="'+esc(merkEmail)+'">';
const feldPw=(id,label,auto,hinweis)=>'<label for="'+id+'">'+t(label)+'</label><div class="pw-feld"><input id="'+id+'" type="password" autocomplete="'+auto+'" minlength="10" maxlength="72" required'+(hinweis?' aria-describedby="'+id+'-hinweis"':'')+'>'
 +'<button type="button" class="pw-zeigen" data-zeige="'+id+'" aria-pressed="false" aria-label="'+t('pwZeigen')+'">'+t('pwZeigenKurz')+'</button></div>'+(hinweis?'<p class="pw-hinweis" id="'+id+'-hinweis">'+t('pwRegel')+'</p>':'');
const feldCode='<label for="access-code">'+t('code')+'</label><input id="access-code" class="code-input" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]*" maxlength="6" placeholder="000000" required>';
const fehlerZeile=()=>'<p class="access-error" id="access-error" role="alert">'+esc(zugangsFehler)+'</p>';
const knopf=k=>'<button class="primary full" type="submit">'+t(k)+'</button>';
const mehr=(...l)=>'<div class="access-more">'+l.map(([id,k])=>'<button type="button" class="text-button" id="'+id+'">'+t(k)+'</button>').join('')+'</div>';
function renderAccess(){
 const kopf='<div class="modal-top"><span class="eyebrow">INVESTTIMER</span><button class="close-button" id="close-access" type="button" aria-label="'+t('close')+'">×</button></div>';
 const recht='<p class="preview-notice">'+(REGISTRIERUNG_RECHT?t('legalLinks'):'')+'</p>';
 const reiter=REGISTRIERUNG_RECHT?'<div class="zugang-reiter" role="tablist"><button type="button" role="tab" id="reiter-anmelden" aria-selected="'+(modus==='anmelden')+'">'+t('login')+'</button>'
  +'<button type="button" role="tab" id="reiter-registrieren" aria-selected="'+(modus==='registrieren')+'">'+t('registerTab')+'</button></div>':'';
 const post=(k,txt)=>'<p>'+esc(t(txt)).replace('{email}','<b>'+esc(gesendet)+'</b>')+'</p>';
 let inhalt;
 switch(modus){
  case 'registrieren':inhalt='<h2 id="access-title" tabindex="-1">'+t('registerTitle')+'</h2>'+reiter+'<ul class="access-benefits"><li>'+t('feature1')+'</li><li>'+t('feature2')+'</li><li>'+t('feature3')+'</li></ul>'
   +'<form id="form-registrieren" class="access-form" novalidate>'+feldEmail()+feldPw('access-pw','pwNeu','new-password',true)+fehlerZeile()+knopf('registerSubmit')+'</form>'+recht;break;
  case 'bestaetigen':inhalt='<h2 id="access-title" tabindex="-1">'+t('confirmTitle')+'</h2>'+post(0,'confirmText')
   +'<form id="form-code" data-typ="signup" class="access-form" novalidate>'+feldCode+fehlerZeile()+knopf('confirmSubmit')+'</form>'
   +mehr(['access-resend','resend'],['zu-anmelden','backToLogin'])+'<p class="preview-notice">'+t('spamHint')+' '+t('alreadyRegistered')+'</p>';break;
  case 'vergessen':inhalt='<h2 id="access-title" tabindex="-1">'+t('forgotTitle')+'</h2><p>'+t('forgotText')+'</p>'
   +'<form id="form-vergessen" class="access-form" novalidate>'+feldEmail()+fehlerZeile()+knopf('forgotSubmit')+'</form>'+mehr(['zu-anmelden','backToLogin']);break;
  case 'zuruecksetzen':inhalt='<h2 id="access-title" tabindex="-1">'+t('resetTitle')+'</h2>'+post(0,'resetText')
   +'<form id="form-zuruecksetzen" class="access-form" novalidate>'+feldCode+feldPw('access-pw','pwNeu','new-password',true)+fehlerZeile()+knopf('resetSubmit')+'</form>'
   +mehr(['access-resend','resend'],['zu-anmelden','backToLogin'])+'<p class="preview-notice">'+t('spamHint')+'</p>';break;
  case 'neu':inhalt='<h2 id="access-title" tabindex="-1">'+t('resetTitle')+'</h2><p>'+t('newPwText')+'</p>'
   +'<form id="form-neu" class="access-form" novalidate>'+feldPw('access-pw','pwNeu','new-password',true)+fehlerZeile()+knopf('resetSubmit')+'</form>';break;
  case 'code-email':inhalt='<h2 id="access-title" tabindex="-1">'+t('codeLoginTitle')+'</h2><p>'+t('codeLoginText')+'</p>'
   +'<form id="form-code-email" class="access-form" novalidate>'+feldEmail()+fehlerZeile()+knopf('sendLink')+'</form>'+mehr(['zu-anmelden','backToLogin']);break;
  case 'code':inhalt='<h2 id="access-title" tabindex="-1">'+t('linkSentTitle')+'</h2>'+post(0,'linkSent')
   +'<form id="form-code" data-typ="email" class="access-form" novalidate>'+feldCode+fehlerZeile()+knopf('codeSubmit')+'</form>'
   +mehr(['access-resend','resend'],['zu-anmelden','backToLogin'])+'<p class="preview-notice">'+t('spamHint')+'</p>';break;
  default:inhalt='<h2 id="access-title" tabindex="-1">'+t('accessTitle')+'</h2>'+reiter
   +'<form id="form-anmelden" class="access-form" novalidate>'+feldEmail('username')+feldPw('access-pw','pw','current-password',false)+fehlerZeile()+knopf('loginSubmit')+'</form>'
   +mehr(['zu-vergessen','forgotLink'],['zu-code','codeLoginLink'])+recht;
 }
 access.innerHTML=kopf+inhalt;
 if(['bestaetigen','zuruecksetzen','code'].includes(modus)){neuKnopf();if(warte()&&!uhr)uhr=setInterval(neuKnopf,1000)}
}
function wechsel(m,fokus){modus=m;zugangsFehler='';renderAccess();($(fokus||'')||$('#access-title'))?.focus({preventScroll:true})}
IT.zugangModus=m=>{if(gesendet&&['bestaetigen','zuruecksetzen','code'].includes(modus)&&m!=='neu')return;modus=m||'anmelden';zugangsFehler=''};
const fertig=()=>{modus='anmelden';gesendet='';zugangsFehler='';closeAccess()};
const zeigeFehler=(text,feld)=>{const f=$('#access-error');if(f){f.classList.remove('ok');f.textContent=text}feld&&feld.focus()};
function fehlerText(c){
 /* Mail-Limit von Supabase (alle Nutzer zusammen): eigener Hinweis und einmal je Tag Meldung an info@ ueber die Fehlererfassung */
 if(c==='over_email_send_rate_limit'){try{IT.fehlerMelden&&IT.fehlerMelden('Anmelde-Mail-Limit erreicht (Supabase over_email_send_rate_limit)','zugang.js',0,'')}catch{}return t('mailLimit')}
 if(c===429||c==='over_request_rate_limit')return t('linkRate');
 if(c==='invalid_credentials'||c==='invalid_grant')return t('pwFalsch');
 if(c==='email_not_confirmed')return t('notConfirmed');
 if(c==='weak_password')return t('pwSchwach');
 if(c==='same_password')return t('pwGleich');
 if(c==='user_already_exists'||c==='email_exists')return t('alreadyRegistered');
 if(c==='otp_expired'||c==='invalid_otp'||c===403)return t('codeInvalid');
  return t('linkFail');
}
async function laeuft(form,fn){
 const k=form.querySelector('button[type=submit]');if(k.disabled)return;const alt=k.textContent;k.disabled=true;k.textContent=t('checking');
 try{return await fn()}finally{k.disabled=false;k.textContent=alt}
}
const pwOk=v=>v.length>=10&&v.length<=72;
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b||!access.contains(b))return;
 if(b.dataset.zeige){const i=$('#'+b.dataset.zeige),an=i.type==='password';i.type=an?'text':'password';b.setAttribute('aria-pressed',an);b.textContent=t(an?'pwVerbergenKurz':'pwZeigenKurz');return}
 const em=$('#access-email');if(em)merkEmail=em.value.trim().toLowerCase();
 if(b.id==='reiter-anmelden')wechsel('anmelden','#access-email');
 else if(b.id==='reiter-registrieren')wechsel('registrieren','#access-email');
 else if(b.id==='zu-anmelden')wechsel('anmelden','#access-email');
 else if(b.id==='zu-vergessen')wechsel('vergessen','#access-email');
 else if(b.id==='zu-code')wechsel('code-email','#access-email');
 else if(b.id==='access-resend'){const typ=modus==='bestaetigen'?'signup':modus==='zuruecksetzen'?'recovery':'email';b.disabled=true;
  try{await IT.erneutSenden(typ,gesendet);sperreBis=Date.now()+60000;const f=$('#access-error');f.textContent=t('resent');f.classList.add('ok')}
  catch(c){zeigeFehler(fehlerText(c));if(c===429)sperreBis=Date.now()+60000}
  neuKnopf();if(!uhr&&warte())uhr=setInterval(neuKnopf,1000)}
});
document.addEventListener('input',e=>{if(e.target.id!=='access-code')return;const v=e.target.value.replace(/\D/g,'').slice(0,6);e.target.value=v;
 if(v.length===6&&e.target.form.id==='form-code')e.target.form.requestSubmit()});
document.addEventListener('submit',async e=>{
 const f=e.target;if(!access.contains(f))return;e.preventDefault();
 const em=$('#access-email'),email=em?em.value.trim().toLowerCase():gesendet,pw=$('#access-pw'),code=$('#access-code');
 if(em){merkEmail=email;if(!emailOk(email))return zeigeFehler(t('emailInvalid'),em)}
 if(code&&!/^\d{6}$/.test(code.value))return zeigeFehler(t('codeShort'),code);
 if(pw&&f.id!=='form-anmelden'&&!pwOk(pw.value))return zeigeFehler(t('pwRegel'),pw);
 if(pw&&!pw.value)return zeigeFehler(t('pwLeer'),pw);
 try{
  if(f.id==='form-anmelden'){await laeuft(f,()=>IT.mitPasswort(email,pw.value));fertig()}
  else if(f.id==='form-registrieren'){const d=await laeuft(f,()=>IT.registrieren(email,pw.value));
   if(d&&d.access_token){fertig();return}gesendet=email;sperreBis=Date.now()+60000;wechsel('bestaetigen','#access-code')}
  else if(f.id==='form-code'){await laeuft(f,()=>IT.pruefeCode(gesendet,code.value,f.dataset.typ));fertig()}
  else if(f.id==='form-vergessen'){await laeuft(f,()=>IT.erneutSenden('recovery',email));gesendet=email;sperreBis=Date.now()+60000;wechsel('zuruecksetzen','#access-code')}
  else if(f.id==='form-zuruecksetzen'){await laeuft(f,async()=>{await IT.pruefeCode(gesendet,code.value,'recovery');await IT.passwortSetzen(pw.value)});fertig()}
  else if(f.id==='form-neu'){await laeuft(f,()=>IT.passwortSetzen(pw.value));IT.neuesPasswort=false;fertig()}
  else if(f.id==='form-code-email'){
   /* Neutral weiter, auch wenn es kein Konto gibt (keine Auskunft, welche Adressen registriert sind) */
   try{await laeuft(f,()=>IT.sendeLink(email))}catch(c){if(!['otp_disabled','user_not_found','signup_disabled',422].includes(c))throw c}
   gesendet=email;sperreBis=Date.now()+60000;wechsel('code','#access-code')}
 }catch(c){
  if(c==='email_not_confirmed'){gesendet=email;IT.erneutSenden('signup',email).catch(()=>{});sperreBis=Date.now()+60000;modus='bestaetigen';zugangsFehler=t('notConfirmed');renderAccess();$('#access-code')?.focus();return}
  zeigeFehler(fehlerText(c),code||pw||em);
 }
});
