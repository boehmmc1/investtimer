/* Mein Konto: Abo-Status, Tarifauswahl (Paywall), Verwaltung, KI-Kontingent, Kontoloeschung.
   Web: Stripe-Checkout und Kundenportal ueber die eigene API. App (Capacitor): Kauf ueber
   window.InvestTimerApp (RevenueCat/Apple), danach Abgleich auf dem Server. */
const app=()=>window.InvestTimerApp||null;
let konto=null,kontoOpener=null,kontoHinweis='',tarifWahl='jaehrlich',kontoAnsicht='konto';
const kontoDlg=document.createElement('dialog');kontoDlg.id='konto-dialog';kontoDlg.className='modal access-dialog konto-dialog';kontoDlg.setAttribute('aria-labelledby','konto-title');document.body.append(kontoDlg);
const datum=ms=>ms?new Date(ms).toLocaleDateString(document.documentElement.lang==='en'?'en-US':'de-DE',{day:'numeric',month:'long',year:'numeric'}):'—';
const verwaltenUrl={apple:'https://apps.apple.com/account/subscriptions',google:'https://play.google.com/store/account/subscriptions'};
function zeile(k,v){return '<div class="konto-zeile"><dt>'+t(k)+'</dt><dd>'+v+'</dd></div>'}
function aboBox(){
 const k=konto;if(!k)return '<p>'+t('alarmLaedt')+'</p>';if(k.fehler)return '<p class="access-error">'+t('alarmFehler')+'</p>';
 if(!k.premium){
  const frei=k.pflicht?t('kontoFrei'):t('kontoFreiOffen');
  return '<p><b>'+t('kontoFreiTitel')+'</b></p><p>'+frei+'</p>'+((app()?app().kaufBereit:k.paywall)?'<button type="button" class="primary full" id="paywall-auf">'+t('premiumAnsehen')+'</button>':'')
   +(k.status==='abgelaufen'||k.status==='erstattet'?'<p class="preview-notice">'+t('kontoAbgelaufen')+' '+datum(k.premiumBis)+'</p>':'');
 }
 const kanal={stripe:t('kanalWeb'),apple:'Apple App Store',google:'Google Play',promo:t('kanalPromo')}[k.kanal]||'—';
 let html='<p><b>'+(k.tarifName||'InvestTimer Premium')+'</b> <span class="konto-status s-'+k.status+'">'+t('st_'+k.status)+'</span></p><dl class="konto-daten">'
  +zeile('kontoPreis',k.preis?k.preis+' / '+t(k.intervall==='Jahr'?'jahr':'monat'):'—')+zeile('kontoKanal',kanal)+zeile('kontoBeginn',datum(k.periodeStart))
  +zeile(k.verlaengerung?'kontoNaechste':'kontoEnde',datum(k.premiumBis))+zeile('kontoAuto',t(k.verlaengerung?'an':'aus'))
  +(k.testTageRest!=null?zeile('kontoTestRest',String(k.testTageRest)):'')+'</dl>';
 if(k.status==='zahlungsproblem')html+='<p class="access-error">'+t('kontoZahlungsproblem')+'</p>';
 if(app()&&k.verwaltung==='stripe')html+='<p class="preview-notice">'+t('aboVerwaltenWebInApp')+'</p>';
 else if(app()&&k.verwaltung==='apple')html+='<button type="button" class="primary full" id="abo-verwalten-apple">'+t('aboVerwalten')+'</button><p class="preview-notice">'+t('aboVerwaltenApple')+'</p>';
 else if(k.verwaltung==='stripe')html+='<button type="button" class="primary full" id="abo-verwalten">'+t('aboVerwalten')+'</button><p class="preview-notice">'+t('aboVerwaltenWeb')+'</p>';
 else if(verwaltenUrl[k.verwaltung])html+='<a class="primary full" id="abo-verwalten-extern" href="'+verwaltenUrl[k.verwaltung]+'" target="_blank" rel="noopener">'+t('aboVerwalten')+'</a><p class="preview-notice">'+t(k.verwaltung==='apple'?'aboVerwaltenApple':'aboVerwaltenGoogle')+'</p>';
 return html;
}
function paywall(){
 const k=konto||{},T=k.tarife||{},test=!k.testGenutzt;
 const karte=(id,extra)=>{const x=T[id]||{};return '<label class="tarif'+(tarifWahl===id?' gewaehlt':'')+'"><input type="radio" name="tarif" value="'+id+'"'+(tarifWahl===id?' checked':'')+'>'
  +'<span class="tarif-kopf"><b>'+t(id==='jaehrlich'?'tarifJahr':'tarifMonat')+'</b>'+(extra||'')+'</span><span class="tarif-preis">'+(x.preis||'')+' <small>/ '+t(id==='jaehrlich'?'jahr':'monat')+'</small></span>'
  +(id==='jaehrlich'?'<small class="tarif-sub">'+t('tarifJahrSub')+'</small>':'')+'</label>'};
 const x=T[tarifWahl]||{},nach=t('tarifDanach').replace('{preis}',x.preis||'').replace('{intervall}',t(tarifWahl==='jaehrlich'?'jahr':'monat'));
 return '<p>'+t('paywallIntro')+'</p><ul class="premium-vorteile">'+['v1','v2','v3','v4','v5'].map(v=>'<li'+(v==='v4'?' class="ki"':'')+'>'+t(v)+'</li>').join('')+'</ul>'
  +'<div class="tarife" role="radiogroup" aria-label="'+t('tarifWahl')+'">'+karte('jaehrlich','<span class="tarif-badge">'+t('tarifSpar')+'</span>')+karte('monatlich')+'</div>'
  +'<p class="tarif-bedingung">'+(test?t('tarifTest').replace('{danach}',nach).replace('{datum}',datum(Date.now()+7*864e5)):nach)+' '+t('tarifAuto')+'</p>'
  +'<p class="access-error" id="paywall-fehler" role="alert">'+esc(kontoHinweis)+'</p>'
  +'<button type="button" class="primary full" id="abo-start">'+t(test?'ctaTest':'ctaAbo')+'</button>'
  +(app()?'<button type="button" class="text-button" id="abo-wiederherstellen">'+t('wiederherstellen')+'</button>':'')
  +'<p class="preview-notice">'+t('paywallFuss')+' <a href="/agb.html" target="_blank" rel="noopener">'+t('agb')+'</a> · <a href="/datenschutz.html" target="_blank" rel="noopener">'+t('datenschutz')+'</a></p>';
}
let pwCode=false,pwMeldung='',pwIstOk=false;
function pwBox(){
 const feld=(id,k,auto)=>'<label for="'+id+'">'+t(k)+'</label><div class="pw-feld"><input id="'+id+'" type="password" autocomplete="'+auto+'" maxlength="72"><button type="button" class="pw-zeigen" data-zeige-konto="'+id+'" aria-pressed="false" aria-label="'+t('pwZeigen')+'">'+t('pwZeigenKurz')+'</button></div>';
 return '<details class="konto-pw"'+(pwMeldung?' open':'')+'><summary>'+t('pwAendernTitel')+'</summary><form id="pw-form" novalidate>'
  +'<input type="email" autocomplete="username" value="'+esc(IT.emailVonSitzung?IT.emailVonSitzung():'')+'" hidden readonly>'
  +(pwCode?'<p>'+t('pwCodeText')+'</p><label for="pw-code">'+t('code')+'</label><input id="pw-code" inputmode="numeric" autocomplete="one-time-code" maxlength="6">':feld('pw-alt','pwAlt','current-password'))
  +feld('pw-neu','pwNeu','new-password')+'<p class="pw-hinweis">'+t('pwRegel')+'</p>'
  +'<p class="'+(pwIstOk?'ok':'access-error')+'" id="pw-meldung" role="status">'+esc(pwMeldung)+'</p><button type="submit" class="primary full">'+t('pwAendernKnopf')+'</button>'
  +(pwCode?'':'<button type="button" class="text-button" id="pw-per-code">'+t('pwOhneAlt')+'</button>')+'</form></details>';
}
function pwAnzeigen(text,ok){pwMeldung=text;pwIstOk=!!ok;const m=$('#pw-meldung');if(m){m.textContent=text;m.className=ok?'ok':'access-error'}}
async function pwCodeAnfordern(){try{await IT.codeFuerAenderung();pwCode=true;pwMeldung=t('pwCodeGesendet');pwIstOk=true;renderKonto();$('#pw-code')?.focus()}catch(c){pwAnzeigen(t(c===429?'linkRate':'linkFail'))}}
kontoDlg.addEventListener('submit',async e=>{if(e.target.id!=='pw-form')return;e.preventDefault();
 const neu=$('#pw-neu').value,alt=$('#pw-alt'),code=$('#pw-code'),k=e.target.querySelector('button[type=submit]');
 if(neu.length<10||neu.length>72)return pwAnzeigen(t('pwRegel'));
 if(code&&!/^\d{6}$/.test(code.value.trim()))return pwAnzeigen(t('codeShort'));
 if(alt&&!alt.value)return pwAnzeigen(t('pwLeer'));
 k.disabled=true;
 try{
  if(alt){try{await IT.mitPasswort(IT.emailVonSitzung(),alt.value)}catch(c){k.disabled=false;return pwAnzeigen(t(c===429?'linkRate':'pwAltFalsch'))}}
  await IT.passwortSetzen(neu,code?code.value.trim():undefined);
  pwCode=false;pwMeldung=t('pwGeaendert');pwIstOk=true;renderKonto();
 }catch(c){k.disabled=false;
  if(c==='reauthentication_needed'){await pwCodeAnfordern();return}
  pwAnzeigen(t(c==='same_password'?'pwGleich':c==='weak_password'?'pwSchwach':c==='reauthentication_not_valid'?'codeInvalid':c===429?'linkRate':'alarmFehler'))}
});
function renderKonto(){
 if(kontoAnsicht==='geloescht'){kontoDlg.innerHTML='<div class="modal-top"><span class="eyebrow">'+t('kontoEyebrow')+'</span><button class="close-button" id="close-konto" type="button" aria-label="'+t('close')+'">×</button></div><h2 id="konto-title" tabindex="-1">'+t('geloeschtTitel')+'</h2><p>'+t('geloeschtText')+'</p>';return}
 const k=konto,ki=k&&k.ki;
 const inhalt=kontoAnsicht==='paywall'?paywall()
  :'<p class="konto-mail">'+esc(t('kontoAngemeldet')).replace('{email}','<b>'+esc((IT.emailVonSitzung&&IT.emailVonSitzung())||'')+'</b>')+'</p>'
  +'<h3 class="konto-abschnitt">'+t('kontoAboTitel')+'</h3><div class="push-box">'+aboBox()+'</div>'
  +(ki&&ki.tag?'<p class="konto-ki">'+t('kontoKi').replace('{n}',ki.heute).replace('{max}',ki.tag)+'</p>':'')
  +pwBox()
  +'<details class="konto-loeschen"><summary>'+t('loeschenTitel')+'</summary><p>'+t('loeschenText')+'</p>'
  +'<label for="loeschen-wort">'+t('loeschenEingabe')+'</label><input id="loeschen-wort" autocomplete="off" autocapitalize="off" spellcheck="false">'
  +'<p class="access-error" id="loeschen-fehler" role="alert">'+(kontoAnsicht==='konto'?esc(kontoHinweis):'')+'</p><button type="button" class="danger full" id="konto-loeschen">'+t('loeschenKnopf')+'</button></details>';
 kontoDlg.innerHTML='<div class="modal-top"><span class="eyebrow">'+t(kontoAnsicht==='paywall'?'paywallEyebrow':'kontoEyebrow')+'</span><button class="close-button" id="close-konto" type="button" aria-label="'+t('close')+'">×</button></div>'
  +'<h2 id="konto-title" tabindex="-1">'+t(kontoAnsicht==='paywall'?'paywallTitel':'kontoTitel')+'</h2>'+inhalt
  +(kontoAnsicht==='paywall'?'<button type="button" class="text-button" id="paywall-zurueck">'+t('zurueck')+'</button>':'');
}
async function ladeKonto(abgleich){
 try{konto=await api(abgleich?'konto/abgleich':'konto',abgleich?{method:'POST'}:{})}catch(x){if(x==='login'||x===401){schliesseKonto();IT.abmelden();return}konto={fehler:true}}
 kontoLink();
}
async function oeffneKonto(opener,ansicht,abgleich){
 kontoOpener=opener;kontoHinweis='';pwCode=false;pwMeldung='';kontoAnsicht=ansicht||'konto';if(!konto)renderKonto();
 if(!kontoDlg.open){kontoDlg.showModal();document.body.classList.add('access-open')}
 await ladeKonto(abgleich);if(kontoAnsicht==='paywall'&&konto&&konto.premium)kontoAnsicht='konto';renderKonto();$('#konto-title').focus({preventScroll:true});
}
function schliesseKonto(){if(kontoDlg.open)kontoDlg.close();document.body.classList.remove('access-open');kontoOpener?.focus({preventScroll:true})}
IT.oeffneKonto=oeffneKonto;
function kontoLink(){document.dispatchEvent(new Event('investtimer:kontomenue'))}
/* Fuer das Kontomenue: Abo-Eintrag erst mit Paywall bzw. Kauf in der App */
IT.aboEintrag=()=>!!(konto&&(konto.premium||(app()?app().kaufBereit:konto.paywall)));
IT.aboAnsicht=()=>konto&&konto.pflicht&&!konto.premium?'paywall':'konto';
async function aboStarten(knopf){
 knopf.disabled=true;kontoHinweis='';
 try{
  if(app()){await app().kaufen(tarifWahl);await ladeKonto(true);kontoAnsicht='konto';renderKonto();IT.loadLive(true);return}
  const d=await api('abo/checkout',{method:'POST',body:JSON.stringify({tarif:tarifWahl})});location.href=d.url;return;
 }catch(x){kontoHinweis=t(x==='schon_premium'?'fehlerSchonPremium':x==='abbruch'?'fehlerAbbruch':x==='zahlung_inaktiv'?'fehlerInaktiv':'alarmFehler')}
 knopf.disabled=false;const f=$('#paywall-fehler');if(f)f.textContent=kontoHinweis;
}
kontoDlg.addEventListener('cancel',e=>{e.preventDefault();schliesseKonto()});
kontoDlg.addEventListener('change',e=>{if(e.target.name==='tarif'){tarifWahl=e.target.value;renderKonto();$('input[name=tarif]:checked')?.focus()}});
kontoDlg.addEventListener('click',async e=>{
 if(e.target===kontoDlg){const r=kontoDlg.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)schliesseKonto();return}
 const b=e.target.closest('button');if(!b)return;
 if(b.id==='close-konto')schliesseKonto();
 else if(b.dataset.zeigeKonto){const i=$('#'+b.dataset.zeigeKonto),an=i.type==='password';i.type=an?'text':'password';b.setAttribute('aria-pressed',an);b.textContent=t(an?'pwVerbergenKurz':'pwZeigenKurz')}
 else if(b.id==='pw-per-code'){b.disabled=true;await pwCodeAnfordern()}
 else if(b.id==='paywall-auf'){kontoAnsicht='paywall';kontoHinweis='';renderKonto();$('#konto-title').focus({preventScroll:true})}
 else if(b.id==='paywall-zurueck'){kontoAnsicht='konto';kontoHinweis='';renderKonto();$('#konto-title').focus({preventScroll:true})}
 else if(b.id==='abo-start')aboStarten(b);
 else if(b.id==='abo-wiederherstellen'){b.disabled=true;try{await app().wiederherstellen();await ladeKonto(true);kontoAnsicht='konto';renderKonto()}catch{b.disabled=false}}
 else if(b.id==='abo-verwalten-apple')app().verwaltenApple();
 else if(b.id==='abo-verwalten'){b.disabled=true;try{location.href=(await api('abo/verwalten',{method:'POST'})).url}catch{b.disabled=false;b.textContent=t('alarmFehler')}}
 else if(b.id==='konto-loeschen'){
  const wort=$('#loeschen-wort').value.trim().toLowerCase(),f=$('#loeschen-fehler');
  if(wort!=='löschen'&&wort!=='loeschen'&&wort!=='delete'){f.textContent=t('loeschenWort');$('#loeschen-wort').focus();return}
  b.disabled=true;
  try{await api('konto/loeschen',{method:'POST',body:JSON.stringify({bestaetigung:'löschen'})});
   const reg=('serviceWorker' in navigator)&&await navigator.serviceWorker.getRegistration().catch(()=>null),abo=reg&&await reg.pushManager?.getSubscription().catch(()=>null);abo&&abo.unsubscribe().catch(()=>{});
   if(app()&&app().abmelden)app().abmelden().catch(()=>{});
   konto=null;kontoAnsicht='geloescht';IT.abmelden();renderKonto();$('#konto-title').focus({preventScroll:true});
  }catch(x){b.disabled=false;f.textContent=t(x==='abo_aktiv'?'loeschenAbo':'alarmFehler')}
 }
});
document.addEventListener('click',e=>{const b=e.target.closest('#konto-link');if(!b)return;e.preventDefault();oeffneKonto(b,konto&&konto.pflicht&&!konto.premium?'paywall':'konto')});
document.addEventListener('investtimer:update',kontoLink);
new MutationObserver(()=>{kontoLink();if(kontoDlg.open)renderKonto()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
(function(){const q=new URLSearchParams(location.search);const abo=q.get('abo'),k=q.get('konto');
 if((abo||k)&&history.replaceState)history.replaceState(null,'',location.pathname+location.hash);
 IT.token().then(tok=>{if(!tok)return;if(abo==='ok'||k)oeffneKonto(null,'konto',abo==='ok');else ladeKonto(false)}).catch(()=>{});
})();
