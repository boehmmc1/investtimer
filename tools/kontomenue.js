/* Kontomenue oben rechts (nur angemeldet): Mein Konto, Meine Alarme, (Abo verwalten), App installieren, Abmelden.
   Ausgeloggt bleibt der Knopf "Anmelden". Kuendigen/Widerrufen gehoeren in die Fusszeile (ohne Login, § 312k/§ 356a BGB). */
const kmKnopf=document.createElement('button');kmKnopf.type='button';kmKnopf.id='konto-knopf';kmKnopf.className='konto-knopf';
kmKnopf.setAttribute('aria-haspopup','menu');kmKnopf.setAttribute('aria-expanded','false');kmKnopf.setAttribute('aria-controls','konto-menue');kmKnopf.hidden=true;
const kmMenue=document.createElement('div');kmMenue.id='konto-menue';kmMenue.className='konto-menue';kmMenue.setAttribute('role','menu');kmMenue.hidden=true;
(()=>{const login=$('#account-login'),werkzeuge=$('.app-header .header-tools');if(login)login.after(kmKnopf);(werkzeuge||document.body).append(kmMenue);kmMenue.setAttribute('aria-labelledby','konto-knopf')})();
const kmEmail=()=>(IT.emailVonSitzung&&IT.emailVonSitzung())||'';
const kmAngemeldet=()=>!!(IT.member&&(IT.session||kmEmail()));
function kmEintraege(){
 const e=[['konto','kontoMenueKonto'],['alarme','kontoMenueAlarme']];
 if(IT.aboEintrag&&IT.aboEintrag())e.push(['abo','kontoMenueAbo']);
 if(IT.installierbar&&IT.installierbar())e.push(['install','installLink']);
 return e;
}
function kmRender(){
 const an=kmAngemeldet(),login=$('#account-login');
 document.body.classList.toggle('konto-angemeldet',an);
 if(login)login.hidden=an;kmKnopf.hidden=!an;
 if(!an){kmSchliessen(false);return}
 const mail=kmEmail(),buchstabe=(mail.trim()[0]||'?').toUpperCase();
 kmKnopf.innerHTML='<span class="konto-kreis" aria-hidden="true">'+esc(buchstabe)+'</span>';
 kmKnopf.setAttribute('aria-label',t('kontoMenueLabel')+(mail?': '+mail:''));
 kmMenue.innerHTML='<div class="konto-menue-mail" role="presentation" title="'+esc(mail)+'">'+esc(mail)+'</div>'
  +kmEintraege().map(([a,k])=>'<button type="button" role="menuitem" tabindex="-1" data-km="'+a+'">'+t(k)+'</button>').join('')
  +'<div class="konto-menue-linie" role="separator"></div><button type="button" role="menuitem" tabindex="-1" data-km="abmelden">'+t('logout')+'</button>';
}
const kmPunkte=()=>[...kmMenue.querySelectorAll('[role=menuitem]')];
function kmOeffnen(zuletzt){
 kmRender();kmMenue.hidden=false;kmKnopf.setAttribute('aria-expanded','true');
 const p=kmPunkte();(zuletzt?p[p.length-1]:p[0])?.focus();
}
function kmSchliessen(fokus){
 if(kmMenue.hidden)return;kmMenue.hidden=true;kmKnopf.setAttribute('aria-expanded','false');if(fokus)kmKnopf.focus();
}
/* Mobil fuehrt der Initialen-Kreis direkt in die Konto-Ansicht, auf dem Desktop oeffnet er das Menue */
IT.kontoMenueZu=()=>kmSchliessen(false);
const kmMobil=()=>matchMedia('(max-width:759px)').matches;
const kmZurAnsicht=()=>{if(location.hash!=='#konto')location.hash='konto';else IT.route&&IT.route()};
kmKnopf.addEventListener('click',()=>{if(kmMobil()){kmSchliessen(false);kmZurAnsicht();return}kmMenue.hidden?kmOeffnen():kmSchliessen(true)});
kmKnopf.addEventListener('keydown',e=>{if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();kmOeffnen(e.key==='ArrowUp')}});
kmMenue.addEventListener('keydown',e=>{
 const p=kmPunkte(),i=p.indexOf(document.activeElement);
 if(e.key==='ArrowDown'){e.preventDefault();p[(i+1)%p.length].focus()}
 else if(e.key==='ArrowUp'){e.preventDefault();p[(i-1+p.length)%p.length].focus()}
 else if(e.key==='Home'){e.preventDefault();p[0].focus()}
 else if(e.key==='End'){e.preventDefault();p[p.length-1].focus()}
 else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();kmSchliessen(true)}
 else if(e.key==='Tab')kmSchliessen(false);
});
kmMenue.addEventListener('click',e=>{
 const b=e.target.closest('[data-km]');if(!b)return;const a=b.dataset.km;kmSchliessen(false);
 if(a==='konto')kmZurAnsicht();
 else if(a==='abo')IT.oeffneKonto(kmKnopf,IT.aboAnsicht?IT.aboAnsicht():'konto');
 else if(a==='alarme')IT.oeffneAlarme(kmKnopf);
 else if(a==='install')IT.oeffneInstall(kmKnopf);
 else if(a==='abmelden'){IT.abmelden();setTimeout(()=>$('#account-login')?.focus(),0)}
});
document.addEventListener('pointerdown',e=>{if(!kmMenue.hidden&&!kmMenue.contains(e.target)&&!kmKnopf.contains(e.target))kmSchliessen(false)},true);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!kmMenue.hidden){kmSchliessen(true)}});
document.addEventListener('investtimer:update',kmRender);
document.addEventListener('investtimer:kontomenue',()=>{if(!kmMenue.hidden){const f=document.activeElement&&document.activeElement.dataset.km;kmRender();(kmMenue.querySelector('[data-km="'+f+'"]')||kmPunkte()[0])?.focus()}else kmRender()});
new MutationObserver(()=>kmRender()).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
kmRender();
