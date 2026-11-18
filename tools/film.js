/* Film-Buehne "So funktioniert InvestTimer": randlose dunkle Flaeche in der Hintergrundfarbe des Films,
   Video ohne Bedienleiste, stumm, in Schleife; startet erst ab 50 % Sichtbarkeit, pausiert ausserhalb.
   Reduzierte Bewegung oder Datensparmodus: nur Poster, Abspielen auf Wunsch. Ersetzt Filmlink und Filmdialog. */
(()=>{
 document.querySelector('.public-context.natural-film')?.remove();
 const ziel=$('#details-panel');if(!ziel)return;
 const sek=document.createElement('section');sek.className='film-buehne';sek.setAttribute('aria-labelledby','film-buehne-titel');
 sek.innerHTML='<div class="film-buehne-innen"><div class="film-buehne-text"><span class="film-eyebrow" data-film="eyebrow"></span>'
  +'<h2 id="film-buehne-titel" data-film="titel"></h2><p data-film="text"></p><p class="film-hinweis" data-film="hinweis"></p></div>'
  +'<div class="film-buehne-film"><video muted playsinline loop preload="metadata" poster="/media/invest-timer-start.jpg" disablepictureinpicture tabindex="-1">'
  +'<source src="/media/invest-timer.webm" type=\'video/webm; codecs="av01.0.05M.08"\'><source src="/media/invest-timer.mp4" type="video/mp4"></video>'
  +'<button type="button" class="film-knopf" data-zustand="pause"><span class="film-knopf-symbol" aria-hidden="true"></span></button></div></div>';
 ziel.after(sek);
 const video=sek.querySelector('video'),knopf=sek.querySelector('.film-knopf');
 video.muted=true;video.defaultMuted=true;video.playsInline=true;
 const ruhig=()=>matchMedia('(prefers-reduced-motion: reduce)').matches||!!(navigator.connection&&navigator.connection.saveData);
 let sichtbar=false,vonHand=null;/* vonHand: 'pause' = Nutzer hat angehalten, 'play' = Nutzer hat gestartet */
 function texte(){
  sek.querySelector('[data-film=eyebrow]').textContent=t('filmEyebrow');sek.querySelector('[data-film=titel]').textContent=t('filmTitel');
  sek.querySelector('[data-film=text]').textContent=t('filmText');sek.querySelector('[data-film=hinweis]').textContent=t('filmHinweis');
  video.setAttribute('aria-label',t('filmAria'));knopfZeigen();
 }
 function knopfZeigen(){const laeuft=!video.paused;knopf.dataset.zustand=laeuft?'laeuft':'pause';knopf.setAttribute('aria-label',t(laeuft?'filmPause':'filmPlay'))}
 function steuern(){
  if(!sichtbar){video.pause();return}
  if(vonHand==='pause')return;
  if(vonHand==='play'||!ruhig())video.play().catch(()=>{});
 }
 video.addEventListener('play',knopfZeigen);video.addEventListener('pause',knopfZeigen);
 knopf.addEventListener('click',()=>{if(video.paused){vonHand='play';video.play().catch(()=>{})}else{vonHand='pause';video.pause()}});
 if('IntersectionObserver' in window)new IntersectionObserver(es=>{for(const e of es){sichtbar=e.intersectionRatio>=.5;steuern()}},{threshold:[0,.5,1]}).observe(video);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();else steuern()});
 new MutationObserver(texte).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 texte();
})();
