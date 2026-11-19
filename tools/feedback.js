/* Feedback-/Kontaktformular als eigene Ansicht (#feedback): mobil Vollbild, Desktop zentrierte Karte (max. 560 px).
   Versand ueber die eigene API (/api/feedback -> Resend an info@investtimer.net). Kein Speichern, keine Cookies.
   Spamschutz: verstecktes Feld (Honeypot), Mindestzeit 3 s, Limits auf dem Server. */
(()=>{
const FT={de:{eyebrow:'FEEDBACK',titel:'Was können wir besser machen?',unter:'Ob Idee, Kritik oder ein Fehler, der dir aufgefallen ist: Wir lesen jede Nachricht.',
 art:'Worum geht es?',idee:'Idee',kritik:'Kritik',fehler:'Fehler gefunden',sonstiges:'Sonstiges',nachricht:'Deine Nachricht',zaehler:'{n} / 2000',
 email:'E-Mail für eine Antwort',optional:'optional',hinweis:'Deine Nachricht geht an info@investtimer.net. Mehr in der <a href="/datenschutz.html">Datenschutzerklärung</a>.',
 absenden:'Absenden',sendet:'Wird gesendet …',danke:'Danke! Deine Nachricht ist angekommen.',zurueck:'Zurück',
 fLeer:'Bitte wähle aus, worum es geht, und schreib mindestens 10 Zeichen.',fEmail:'Bitte prüf die E-Mail-Adresse.',
 fVersand:'Das hat nicht geklappt. Schreib uns direkt an info@investtimer.net.',fLimit:'Für heute sind schon viele Nachrichten von hier gekommen. Schreib uns gern direkt an info@investtimer.net.',
 fSchnell:'Einen kleinen Moment noch, dann klappt das Absenden.',ehp:'Bitte nicht ausfüllen'},
en:{eyebrow:'FEEDBACK',titel:'What can we do better?',unter:'Whether it’s an idea, criticism or a bug you noticed: we read every message.',
 art:'What is it about?',idee:'Idea',kritik:'Criticism',fehler:'Found a bug',sonstiges:'Other',nachricht:'Your message',zaehler:'{n} / 2000',
 email:'Email for a reply',optional:'optional',hinweis:'Your message goes to info@investtimer.net. More in our <a href="/datenschutz.html">privacy policy</a> (in German).',
 absenden:'Send',sendet:'Sending …',danke:'Thanks! Your message has arrived.',zurueck:'Back',
 fLeer:'Please choose a topic and write at least 10 characters.',fEmail:'Please check the email address.',
 fVersand:'That didn’t work. Email us directly at info@investtimer.net.',fLimit:'We’ve already received a lot of messages from here today. Feel free to email us at info@investtimer.net.',
 fSchnell:'One moment, then you can send.',ehp:'Please leave empty'}};
const ft=k=>FT[document.documentElement.lang==='en'?'en':'de'][k];
const angemeldet=()=>!!(IT.member&&(IT.session||(IT.emailVonSitzung&&IT.emailVonSitzung())));
const ARTEN=['idee','kritik','fehler','sonstiges'];
const z={art:'',text:'',email:null,geoeffnet:0,fertig:false,meldung:'',busy:false,herkunft:'stress'};
const sicht=document.createElement('section');sicht.id='feedback-ansicht';sicht.className='feedback-ansicht';sicht.hidden=true;sicht.setAttribute('aria-labelledby','feedback-titel');
($('#konto-ansicht')||$('.app-header'))?.after(sicht);
function html(){
 if(z.fertig)return '<div class="feedback-karte feedback-fertig" role="status"><span class="eyebrow feedback-eyebrow">'+ft('eyebrow')+'</span><h2 id="feedback-titel" tabindex="-1">'+esc(ft('danke'))+'</h2><button type="button" class="primary feedback-zurueck" data-fb="zurueck">'+esc(ft('zurueck'))+'</button></div>';
 const mail=z.email!=null?z.email:(angemeldet()&&IT.emailVonSitzung?IT.emailVonSitzung():'');
 return '<form class="feedback-karte" id="feedback-form" novalidate><span class="eyebrow feedback-eyebrow">'+ft('eyebrow')+'</span><h2 id="feedback-titel" tabindex="-1">'+esc(ft('titel'))+'</h2><p class="feedback-unter">'+esc(ft('unter'))+'</p>'
  +'<fieldset class="feedback-arten"><legend>'+esc(ft('art'))+'</legend><div class="feedback-chips" role="radiogroup" aria-label="'+esc(ft('art'))+'">'
  +ARTEN.map(a=>'<button type="button" role="radio" class="feedback-chip" data-art="'+a+'" aria-checked="'+(z.art===a)+'" tabindex="'+((z.art?z.art===a:a==='idee')?0:-1)+'">'+esc(ft(a))+'</button>').join('')+'</div></fieldset>'
  +'<label for="feedback-text">'+esc(ft('nachricht'))+'</label><textarea id="feedback-text" rows="6" maxlength="2000" required>'+esc(z.text)+'</textarea>'
  +'<p class="feedback-zaehler" id="feedback-zaehler" aria-live="polite">'+esc(ft('zaehler').replace('{n}',z.text.length))+'</p>'
  +'<label for="feedback-email">'+esc(ft('email'))+(angemeldet()?'':' <span class="feedback-optional">('+esc(ft('optional'))+')</span>')+'</label><input id="feedback-email" type="email" inputmode="email" autocomplete="email" maxlength="200" value="'+esc(mail)+'">'
  +'<div class="feedback-hp" aria-hidden="true"><label for="feedback-website">'+esc(ft('ehp'))+'</label><input id="feedback-website" name="website" type="text" tabindex="-1" autocomplete="off"></div>'
  +'<p class="feedback-hinweis">'+ft('hinweis')+'</p>'
  +'<p class="access-error feedback-meldung" id="feedback-meldung" role="alert">'+esc(z.meldung)+'</p>'
  +'<button type="submit" class="primary full feedback-absenden"'+(z.busy?' disabled':'')+'>'+esc(z.busy?ft('sendet'):ft('absenden'))+'</button></form>';
}
function zeichne(fokus){const f=document.activeElement&&sicht.contains(document.activeElement)?document.activeElement.id:null;sicht.innerHTML=html();
 if(fokus)$('#feedback-titel')?.focus({preventScroll:true});else if(f)$('#'+f)?.focus({preventScroll:true})}
function melde(k){z.meldung=k?ft(k):'';const m=$('#feedback-meldung');if(m)m.textContent=z.meldung}
sicht.addEventListener('input',e=>{if(z.meldung)melde('');if(e.target.id==='feedback-text'){z.text=e.target.value;const c=$('#feedback-zaehler');if(c)c.textContent=ft('zaehler').replace('{n}',z.text.length)}
 else if(e.target.id==='feedback-email')z.email=e.target.value});
sicht.addEventListener('click',e=>{
 const c=e.target.closest('[data-art]');if(c){z.art=c.dataset.art;if(z.meldung)melde('');sicht.querySelectorAll('[data-art]').forEach(b=>{const an=b===c;b.setAttribute('aria-checked',String(an));b.tabIndex=an?0:-1});c.focus();return}
 if(e.target.closest('[data-fb=zurueck]')){z.fertig=false;z.text='';z.art='';z.meldung='';if(history.length>1&&z.herkunft!=='feedback')history.back();else location.hash='konto'}
});
sicht.addEventListener('keydown',e=>{const c=e.target.closest('[data-art]');if(!c||!['ArrowRight','ArrowLeft','ArrowDown','ArrowUp'].includes(e.key))return;e.preventDefault();
 const i=ARTEN.indexOf(c.dataset.art),n=ARTEN[(i+(e.key==='ArrowRight'||e.key==='ArrowDown'?1:3))%4];sicht.querySelector('[data-art="'+n+'"]').click()});
sicht.addEventListener('submit',async e=>{
 e.preventDefault();if(z.busy)return;
 const text=z.text.trim(),mail=($('#feedback-email')?.value||'').trim();
 if(!z.art||text.length<10){melde('fLeer');(z.art?$('#feedback-text'):sicht.querySelector('[data-art]'))?.focus();return}
 if(mail&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)){melde('fEmail');$('#feedback-email')?.focus();return}
 const warten=3000-(Date.now()-z.geoeffnet);if(warten>0){melde('fSchnell');return}
 z.busy=true;melde('');zeichne();
 let ok=false,fehler='fVersand';
 try{const tok=IT.token?await IT.token().catch(()=>null):null;
  const r=await fetch('/api/feedback',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json',...(tok?{Authorization:'Bearer '+tok}:{})},
   body:JSON.stringify({kategorie:z.art,nachricht:text,email:mail,website:$('#feedback-website')?.value||'',dauer:Date.now()-z.geoeffnet,
    sprache:document.documentElement.lang,ansicht:z.herkunft,version:(window.INVESTTIMER_VERSION||'')})});
  ok=r.ok;if(r.status===429)fehler='fLimit';else if(r.status===400){const d=await r.json().catch(()=>({}));fehler=d.error==='email'?'fEmail':d.error==='zu_schnell'?'fSchnell':d.error==='leer'?'fLeer':'fVersand'}
 }catch{ok=false}
 z.busy=false;if(ok){z.fertig=true;zeichne(true)}else{z.meldung=ft(fehler);zeichne()}
});
addEventListener('hashchange',e=>{const alt=(e.oldURL.split('#')[1]||'stress');if(location.hash==='#feedback'&&alt!=='feedback')z.herkunft=alt});
IT.feedbackAnsicht={zeigen(){const war=sicht.hidden;sicht.hidden=false;if(war){z.geoeffnet=Date.now();if(!z.fertig)z.meldung='';zeichne()}},verbergen(){sicht.hidden=true;if(z.fertig){z.fertig=false;z.text='';z.art=''}}};
new MutationObserver(()=>{if(!sicht.hidden)zeichne()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
document.addEventListener('investtimer:update',()=>{if(!sicht.hidden&&!z.busy)zeichne()});
})();
