/* Erklaerfilm. Schalter IT_FILM (beim Bauen, /root/volafly-chat/.env), aus: kein Film auf der Seite.
   Ausgeloggt: Film-Karte rechts neben dem Wert (ab 761 px) bzw. zwischen Bogen und Knopf (mobil);
   stumm, Schleife, ohne Bedienleiste, startet erst ab 50 % Sichtbarkeit und pausiert ausserhalb.
   Reduzierte Bewegung oder Datensparmodus: nur Poster, Abspielen auf Wunsch.
   Eingeloggt: kein Film in der Hauptansicht, nur eine kleine Karte unter "Mehr erfahren", Abspielen auf Klick an derselben Stelle. */
(()=>{
 document.querySelector('.public-context.natural-film')?.remove();
 if(!__FILM_AN__)return;
 const QUELLEN='<source src="/media/invest-timer.webm" type=\'video/webm; codecs="av01.0.05M.08"\'><source src="/media/invest-timer.mp4" type="video/mp4">';
 const VIDEO=poster=>'<video muted playsinline loop preload="metadata" poster="'+poster+'" disablepictureinpicture disableremoteplayback tabindex="-1">'+QUELLEN+'</video>'
  +'<button type="button" class="film-knopf" data-zustand="pause"><span class="film-knopf-symbol" aria-hidden="true"></span></button>';
 const ruhig=()=>matchMedia('(prefers-reduced-motion: reduce)').matches||!!(navigator.connection&&navigator.connection.saveData);
 const istMitglied=()=>document.body.classList.contains('members-layout');
 function spieler(karte,auto){
  const video=karte.querySelector('video'),knopf=karte.querySelector('.film-knopf');
  video.muted=true;video.defaultMuted=true;video.playsInline=true;
  let sichtbar=false,vonHand=null,aktiv=false;/* vonHand: 'pause' = angehalten, 'play' = gestartet */
  const zeigen=()=>{const l=!video.paused;knopf.dataset.zustand=l?'laeuft':'pause';knopf.setAttribute('aria-label',t(l?'filmPause':'filmPlay'))};
  const steuern=()=>{
   if(!aktiv||!sichtbar||document.hidden){if(!video.paused)video.pause();return}
   if(vonHand==='pause')return;
   if(vonHand==='play'||(auto&&!ruhig()))video.play().catch(()=>{});
  };
  const start=()=>{if(video.paused){vonHand='play';karte.classList.add('gestartet');video.play().catch(()=>{})}else{vonHand='pause';video.pause()}};
  video.addEventListener('play',zeigen);video.addEventListener('pause',zeigen);
  knopf.addEventListener('click',start);
  if(!auto)video.addEventListener('click',()=>{if(video.paused)start()});
  new IntersectionObserver(es=>{for(const e of es)sichtbar=e.isIntersecting&&e.intersectionRatio>=.5;steuern()},{threshold:[0,.5,1]}).observe(video);
  document.addEventListener('visibilitychange',steuern);
  return {zeigen,steuern,aktiv(v){if(aktiv===v)return;aktiv=v;if(!v&&!auto){vonHand=null;karte.classList.remove('gestartet')}steuern()}};
 }

 /* Ausgeloggt: Film-Karte */
 const karte=document.createElement('aside');karte.className='film-karte';karte.setAttribute('aria-labelledby','film-karte-titel');
 karte.innerHTML='<div class="film-karte-bild">'+VIDEO('/media/invest-timer-start.jpg')+'</div>'
  +'<div class="film-karte-text"><span class="film-eyebrow" id="film-karte-titel"></span><p class="film-satz"></p><p class="film-hinweis"></p></div>';
 const oeffentlich=spieler(karte,true),breit=matchMedia('(min-width:761px)');

 /* Eingeloggt: kleine Karte unter "Mehr erfahren" */
 const mini=document.createElement('section');mini.className='film-mini';mini.setAttribute('aria-labelledby','film-mini-titel');
 mini.innerHTML='<div class="film-mini-bild">'+VIDEO('/media/invest-timer-standbild.jpg')+'</div>'
  +'<div class="film-mini-text"><span class="film-eyebrow"></span><h3 id="film-mini-titel"></h3><p class="film-hinweis"></p></div>';
 const klein=spieler(mini,false),panel=$('#details-panel');

 function platzieren(){
  const mitglied=istMitglied(),first=$('.first-look'),spalte=$('.score-column'),knopf=$('#subscribe-module');
  document.body.classList.toggle('mit-film',!mitglied);
  /* Desktop: Ueberschrift ueber beide Spalten, damit Wert und Film-Karte gleich hoch stehen */
  const zweck=$('.public-purpose');
  if(zweck&&first&&spalte){if(!mitglied&&breit.matches){if(zweck.parentNode!==first)first.prepend(zweck)}else if(zweck.parentNode!==spalte)spalte.prepend(zweck)}
  if(mitglied){karte.remove()}
  else if(breit.matches){if(spalte&&spalte.nextElementSibling!==karte)spalte.after(karte)}
  else if(knopf&&knopf.previousElementSibling!==karte)knopf.before(karte);
  oeffentlich.aktiv(!mitglied);
  const unten=panel&&panel.querySelector('.detail-bottom');
  if(mitglied&&unten){if(unten.previousElementSibling!==mini)unten.before(mini)}else if(!mitglied)mini.remove();
  klein.aktiv(mitglied&&!!panel&&!panel.hidden);
 }
 function texte(){
  karte.querySelector('.film-eyebrow').textContent=t('filmEyebrow');karte.querySelector('.film-satz').textContent=t('filmSatz');
  karte.querySelector('.film-hinweis').textContent=t('filmHinweis');
  mini.querySelector('.film-eyebrow').textContent=t('filmEyebrow');mini.querySelector('h3').textContent=t('filmTitel');
  mini.querySelector('.film-hinweis').textContent=t('filmHinweis');
  for(const v of [karte,mini])v.querySelector('video').setAttribute('aria-label',t('filmAria'));
  oeffentlich.zeigen();klein.zeigen();
 }
 breit.addEventListener('change',platzieren);
 new MutationObserver(platzieren).observe(document.body,{attributes:true,attributeFilter:['class']});
 if(panel)new MutationObserver(platzieren).observe(panel,{childList:true,attributes:true,attributeFilter:['hidden']});
 new MutationObserver(texte).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 texte();platzieren();
})();
