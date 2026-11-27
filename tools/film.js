/* Erklaerfilm "So liest du den Marktstress" (Auftrag 25.11.2026, Block G). Schalter IT_FILM (beim Bauen), aus: keine Karte.
   Nur ausgeloggt, auf der Startseite direkt unter der Aufbau-Karte: Standbild 16:9 mit rundem Abspielknopf, darunter Label und Titel.
   Das Video wird erst beim Tippen geladen (vorher nur das Standbild, nichts sonst); kein Autoplay, keine Tonspur, inline mit Steuerelementen.
   Reduzierte Bewegung: ebenso nur Standbild bis zum Tippen. Eingeloggt erscheint die Karte nicht. */
(()=>{
 document.querySelector('.public-context.natural-film')?.remove();
 if(!__FILM_AN__)return;
 const FT={de:{label:'KURZ ERKLÄRT',titel:'So liest du den Marktstress',aria:'Film abspielen: So liest du den Marktstress',video:'Erklärfilm: So liest du den Marktstress'},
  en:{label:'EXPLAINED',titel:'How to read market stress',aria:'Play film: How to read market stress',video:'Explainer film: How to read market stress'}};
 const ft=k=>FT[document.documentElement.lang==='en'?'en':'de'][k];
 const karte=document.createElement('section');karte.id='film-karte';karte.className='film-karte2';karte.setAttribute('aria-labelledby','film-titel');
 karte.innerHTML='<div class="film-bild"><img src="/media/film-standbild.jpg" alt="" width="640" height="360" loading="lazy" decoding="async">'
  +'<button type="button" class="film-play"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z"/></svg></button></div>'
  +'<div class="film-text"><span class="film-label"></span><h3 id="film-titel"></h3></div>';
 const bild=karte.querySelector('.film-bild'),knopf=karte.querySelector('.film-play');
 knopf.addEventListener('click',()=>{
  const v=document.createElement('video');v.src='/media/film-marktstress.mp4';v.controls=true;v.playsInline=true;v.setAttribute('playsinline','');v.muted=true;
  v.preload='auto';v.poster='/media/film-standbild.jpg';v.setAttribute('aria-label',ft('video'));v.disableRemotePlayback=true;
  bild.replaceChildren(v);v.play().catch(()=>{});v.focus({preventScroll:true});
  try{IT.zaehlen&&IT.zaehlen('film')}catch{}
 });
 function texte(){karte.querySelector('.film-label').textContent=ft('label');karte.querySelector('#film-titel').textContent=ft('titel');knopf.setAttribute('aria-label',ft('aria'))}
 function platzieren(){
  const aus=!IT.member,ziel=$('#aufbau-karte')||$('.assessment');
  if(!aus){const v=karte.querySelector('video');if(v)v.pause();karte.remove();return}
  if(ziel&&ziel.nextElementSibling!==karte)ziel.after(karte);
 }
 document.addEventListener('investtimer:update',platzieren);
 new MutationObserver(texte).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 texte();platzieren();
})();
