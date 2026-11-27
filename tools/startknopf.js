/* Logo "InvestTimer" oben links als Startseiten-Knopf (Nachtrag L, 27.11.2026). Web, mobil, installierte Web-App, ein- und ausgeloggt.
   - aus einem anderen Reiter oder dem Konto: offene Blaetter/Menues/Info-Felder schliessen, Ansicht Marktstress, ganz oben (Verlaufseintrag)
   - ungespeicherte Eingaben im Alarm-Blatt: Rueckfrage "Aenderungen verwerfen?"
   - Startseite gescrollt: sanft nach oben (reduzierte Bewegung: sofort)
   - Startseite oben: Wert neu laden wie bei der Rueckkehr in die App (no-store), Lade-Hinweis an der Pille bzw. ausgeloggt an der
     Hinweiszeile, danach kurz "Aktualisiert"; hoechstens alle 10 Sekunden
   - eine laufende KI-Unterhaltung bleibt erhalten (sie liegt im Speicher der Seite, der Wechsel laedt nichts neu)
   Offene modale Blaetter machen den Rest der Seite inert: ein Tippen auf die Stelle des Logos landet dann auf dem Hintergrund des
   Blatts und wird hier als Logo-Tippen behandelt. */
(()=>{
const logo=document.querySelector('a.wordmark[data-start-knopf]');if(!logo)return;
const LT={de:{aria:'Zur Startseite',frage:'Änderungen verwerfen?',frageText:'Dein Alarm ist noch nicht gespeichert.',verwerfen:'Verwerfen',bleiben:'Weiter bearbeiten',laedt:'Wird aktualisiert …',ok:'Aktualisiert'},
 en:{aria:'Home',frage:'Discard changes?',frageText:'Your alert has not been saved yet.',verwerfen:'Discard',bleiben:'Keep editing',laedt:'Updating …',ok:'Up to date'}};
const lt=k=>LT[document.documentElement.lang==='en'?'en':'de'][k];
const ruhig=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
function texte(){logo.setAttribute('aria-label',lt('aria'))}
new MutationObserver(texte).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});texte();

/* Ansage fuer Screenreader */
const ansage=document.createElement('span');ansage.className='start-ansage';ansage.setAttribute('role','status');document.body.append(ansage);

/* Rueckfrage bei ungespeichertem Alarm (eigenes kleines Blatt ueber dem Alarm-Blatt) */
let frage=null;
function rueckfrage(){return new Promise(fertig=>{
 if(!frage){frage=document.createElement('dialog');frage.className='start-frage';frage.setAttribute('aria-labelledby','start-frage-titel');document.body.append(frage)}
 frage.innerHTML='<h2 id="start-frage-titel">'+esc(lt('frage'))+'</h2><p>'+esc(lt('frageText'))+'</p><div class="start-frage-knoepfe">'
  +'<button type="button" class="text-button" data-start="bleiben">'+esc(lt('bleiben'))+'</button><button type="button" class="primary warn" data-start="verwerfen">'+esc(lt('verwerfen'))+'</button></div>';
 let antwort=false;
 const klick=e=>{const b=e.target.closest('[data-start]');if(b){antwort=b.dataset.start==='verwerfen';frage.close()}else if(e.target===frage)frage.close()};
 frage.addEventListener('click',klick);
 frage.addEventListener('close',()=>{frage.removeEventListener('click',klick);fertig(antwort)},{once:true});
 frage.showModal();frage.querySelector('[data-start=bleiben]').focus();
})}

function allesSchliessen(){
 document.querySelectorAll('dialog[open]').forEach(d=>{try{d.close()}catch{}});
 document.body.classList.remove('access-open','assistant-open','alarm-blatt-offen');
 IT.kontoMenueZu&&IT.kontoMenueZu();
 IT.kiInfoZu&&IT.kiInfoZu();
 const vi=document.querySelector('#verlauf-info-text');if(vi&&!vi.hidden){vi.hidden=true;document.querySelector('.verlauf-info')?.setAttribute('aria-expanded','false')}
 document.activeElement&&document.activeElement!==document.body&&document.activeElement.blur&&document.activeElement.blur();
}

/* Neuladen: dieselbe Funktion wie bei der Rueckkehr in die App, Sperre 10 s */
const SPERRE=10000;let letztesNeu=0,ladeTimer=0;
function hinweisZiel(){
 if(IT.member){const p=document.querySelector('.snapshot-label');return p&&p.offsetParent?p:null}
 const z=document.querySelector('#zeitversatz-zeile');return z&&!z.hidden?z:null;
}
function neuLaden(){
 const jetzt=Date.now();if(jetzt-letztesNeu<SPERRE)return false;letztesNeu=jetzt;
 const ziel=hinweisZiel(),t0=jetzt;
 document.querySelectorAll('.start-laedt,.start-frisch').forEach(x=>x.classList.remove('start-laedt','start-frisch'));
 if(ziel){ziel.classList.add('start-laedt');ziel.setAttribute('aria-busy','true')}
 ansage.textContent=lt('laedt');
 const ende=()=>{beob.disconnect();clearTimeout(ladeTimer);
  const rest=Math.max(0,450-(Date.now()-t0));   /* Lade-Hinweis kurz sichtbar lassen, kein Flackern */
  setTimeout(()=>{const z=hinweisZiel()||ziel;ziel&&ziel.classList.remove('start-laedt');ziel&&ziel.removeAttribute('aria-busy');
   if(z){z.dataset.startOk=lt('ok');z.classList.add('start-frisch');setTimeout(()=>z.classList.remove('start-frisch'),1800)}
   ansage.textContent=lt('ok');setTimeout(()=>{ansage.textContent=''},2500)},rest)};
 const beob=new MutationObserver(()=>{if(document.body.dataset.live==='fertig')ende()});
 beob.observe(document.body,{attributes:true,attributeFilter:['data-live']});
 ladeTimer=setTimeout(ende,8000);
 if(IT.loadLive){IT.loadLive(true);if(document.body.dataset.live!=='laedt')ende()}else ende();
 IT.updatePruefen&&IT.updatePruefen();
 return true;
}

async function startTippen(){
 if(IT.alarmBlattGeaendert&&IT.alarmBlattGeaendert()){if(!await rueckfrage())return;IT.alarmBlattZu&&IT.alarmBlattZu()}
 const offen=!!document.querySelector('dialog[open]')||(document.querySelector('#konto-menue')&&!document.querySelector('#konto-menue').hidden);
 allesSchliessen();
 const ansicht=IT.aktiveAnsicht?IT.aktiveAnsicht():'stress';
 if(ansicht!=='stress'){IT.zurStartseite?IT.zurStartseite():(location.hash='');return}
 if(window.scrollY>4){window.scrollTo({top:0,behavior:ruhig()?'auto':'smooth'});return}
 if(!offen)neuLaden();
}
logo.addEventListener('click',e=>{
 if(e.button>0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;   /* neuer Tab / neues Fenster wie bei jedem Link */
 e.preventDefault();startTippen();
});
/* Blatt offen: Tippen auf die Stelle des Logos (Hintergrund des modalen Blatts) */
addEventListener('click',e=>{
 const d=e.target;if(!(d instanceof HTMLDialogElement)||!d.open||d===frage)return;
 const r=logo.getBoundingClientRect(),x=e.clientX,y=e.clientY;
 if(r.width&&x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom){e.stopImmediatePropagation();e.preventDefault();startTippen()}
},true);
IT.startTippen=startTippen;
})();
