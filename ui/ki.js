(() => {
/* 05 · InvestTimer KI: Fragenkarten, Autocomplete, Chat. Sichtbar nur, wenn /api/chat erreichbar ist.
   Der Halbmond ist das Zeichen des Bots: gefuellt bis zum aktuellen Marktstress, waehrend einer Antwort laeuft er als Denk-Anzeige. */
'use strict';
const KATS=__KI_KATEGORIEN__;
const API='/api/chat',PRO_SEITE=3,MAX_VERLAUF=6,START_FRAGE=KATS[0]?.fragen[0];
const $=s=>document.querySelector(s);
const sec=$('#ki'),openBtn=$('#ki-open'),input=$('#ki-input'),sendBtn=$('#ki-send'),log=$('#ki-log'),ac=$('#ki-ac'),cards=$('#ki-cards'),composer=$('#ki-composer'),resetBtn=$('#ki-reset'),closeBtn=$('#ki-close');
if(!sec||!input)return;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const seiten=k=>Math.ceil(k.fragen.length/PRO_SEITE);
const ALLE=KATS.flatMap(k=>k.fragen.map(q=>({q,kat:k.kurz.toUpperCase()})));
const mobil=matchMedia('(max-width:760px)');
const state={messages:[],loading:false,available:false,sheet:false,neu:-1,wert:null,seite:KATS.map(k=>Math.floor(Math.random()*seiten(k))),kat:0,acIndex:0,acZu:true,treffer:[]};
const ICON={
 gauge:'<path d="M4 17a8 8 0 0 1 16 0"/><path d="m12 17-3.5-5.5"/>',
 activity:'<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
 bars:'<line x1="6" y1="20" x2="6" y2="11"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="18" y1="20" x2="18" y2="14"/>',
 rotate:'<path d="M21 12a9 9 0 1 1-2.6-6.4"/><polyline points="21 3 21 8 16 8"/>'
};
const icon=n=>`<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[n]||''}</svg>`;
const BOGEN='d="M6 34a18 18 0 0 1 36 0" pathLength="100"';
const mark=(denkt=false)=>`<svg class="ki-mark${denkt?' denkt':''}" viewBox="3 13 42 24" aria-hidden="true"><path class="ki-mark-track" ${BOGEN}/><path class="ki-mark-fill" ${BOGEN}/></svg>`;

/* Aktueller Wert aus dem Signalbogen: fuellt die Halbmond-Zeichen und benennt den Einstieg */
function setzeWert(v){
 state.wert=Number.isFinite(v)?Math.round(v):null;
 const fill=state.wert===null?0:state.wert;
 sec.style.setProperty('--ki-wert',fill);if(openBtn)openBtn.style.setProperty('--ki-wert',fill);
 renderOpen();
}
document.addEventListener('investtimer:wert',e=>setzeWert(e.detail));
function renderOpen(){
 if(!openBtn)return;
 const frage=state.wert===null?'Was steckt hinter dem Marktstress?':`Was treibt die ${state.wert}?`;
 openBtn.innerHTML=`<svg viewBox="3 13 42 24" aria-hidden="true" class="ki-glyph"><path class="ki-glyph-track" ${BOGEN}/><path class="ki-glyph-fill" ${BOGEN}/></svg><span><strong>${esc(frage)}</strong> <span class="ki-open-sub">KI fragen</span></span>`;
 openBtn.setAttribute('aria-label',frage+' – InvestTimer KI fragen');
}

/* Sichtbarkeit: nur mit erreichbarem Backend und in der deutschen Ansicht */
function syncVisible(){const show=state.available&&document.documentElement.lang!=='en';sec.hidden=!show;if(openBtn)openBtn.hidden=!show;if(!show)schliesseSheet()}
new MutationObserver(syncVisible).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
if(location.protocol.startsWith('http'))fetch(API,{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{state.available=!!(d&&d.ok);syncVisible()}).catch(()=>{});
if(openBtn)openBtn.addEventListener('click',()=>{
 if(!state.messages.length&&START_FRAGE){input.value=START_FRAGE;senden()}
 if(!state.sheet)sec.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
 if(!state.messages.length)input.focus({preventScroll:true});
});

/* App-Ansicht (schmale Bildschirme): laufendes Gespraech als Vollbild mit Eingabe unten */
let scrollVorher=0;
function oeffneSheet(){if(!mobil.matches||state.sheet)return;state.sheet=true;scrollVorher=window.scrollY;sec.classList.add('ki-sheet');document.documentElement.classList.add('ki-lock');closeBtn.hidden=false}
/* Schliessen fuehrt dorthin zurueck, wo das Gespraech begonnen wurde */
function schliesseSheet(){if(!state.sheet)return;state.sheet=false;sec.classList.remove('ki-sheet');document.documentElement.classList.remove('ki-lock');closeBtn.hidden=true;window.scrollTo(0,scrollVorher)}
closeBtn.addEventListener('click',schliesseSheet);
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&state.sheet&&!state.treffer.length)schliesseSheet()});
mobil.addEventListener('change',()=>{if(!mobil.matches)schliesseSheet()});

/* Fragenkarten */
function renderCards(){
 cards.innerHTML=`<div class="ki-tabs" role="tablist" aria-label="Kategorien">${KATS.map((k,i)=>`<button type="button" role="tab" aria-selected="${i===state.kat}" data-ki-tab="${i}">${esc(k.kurz)}</button>`).join('')}</div><div class="ki-grid">${KATS.map((k,i)=>{
  const s=state.seite[i],n=seiten(k),fragen=k.fragen.slice(s*PRO_SEITE,s*PRO_SEITE+PRO_SEITE);
  return `<div class="ki-card${i===state.kat?' on':''}"><div class="ki-card-top"><span>${icon(k.icon)}${esc(k.kurz)}</span>${n>1?`<button type="button" class="ki-shuffle" data-ki-shuffle="${i}" aria-label="Andere Fragen zu ${esc(k.kurz)} zeigen" title="Andere Fragen">${icon('rotate')}</button>`:''}</div>${fragen.map(q=>`<button type="button" class="ki-q" data-ki-q="${esc(q)}">${esc(q)}</button>`).join('')}<div class="ki-dots" aria-hidden="true">${n>1?Array.from({length:n},(_,j)=>`<i${j===s?' class="on"':''}></i>`).join(''):''}</div></div>`}).join('')}</div>`;
}
let touchX=0;
cards.addEventListener('touchstart',e=>{touchX=e.touches[0].clientX},{passive:true});
cards.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>40&&getComputedStyle(cards.querySelector('.ki-tabs')).display!=='none'){state.kat=(state.kat+(dx<0?1:KATS.length-1))%KATS.length;renderCards()}},{passive:true});
cards.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 if(b.dataset.kiTab!==undefined){state.kat=Number(b.dataset.kiTab);renderCards()}
 else if(b.dataset.kiShuffle!==undefined){const i=Number(b.dataset.kiShuffle);state.seite[i]=(state.seite[i]+1)%seiten(KATS[i]);renderCards()}
 else if(b.dataset.kiQ)uebernehmen(b.dataset.kiQ)});

/* Autocomplete: ab 3 Zeichen, alle Suchwoerter muessen vorkommen, hoechstens 4 Treffer */
const woerter=()=>input.value.trim().toLowerCase().split(/\s+/).filter(w=>w.length>=2);
function markieren(text){const w=woerter();if(!w.length)return esc(text);
 const re=new RegExp('('+w.map(x=>x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|')+')','gi');
 return text.split(re).map((t,i)=>i%2===1?`<strong>${esc(t)}</strong>`:esc(t)).join('')}
function renderAc(){
 const w=woerter();
 state.treffer=(state.messages.length===0&&!state.acZu&&input.value.trim().length>=3&&w.length)?ALLE.filter(f=>w.every(x=>f.q.toLowerCase().includes(x))).slice(0,4):[];
 const offen=state.treffer.length>0;state.acIndex=Math.min(state.acIndex,Math.max(0,state.treffer.length-1));
 ac.hidden=!offen;composer.classList.toggle('open',offen);cards.classList.toggle('dim',offen);input.setAttribute('aria-expanded',String(offen));
 ac.innerHTML=offen?state.treffer.map((t,i)=>`<button type="button" role="option" aria-selected="${i===state.acIndex}" data-ki-ac="${i}"><span>${markieren(t.q)}</span><small>${esc(t.kat)}</small></button>`).join('')+`<div class="ki-ac-hint"><span>↑ ↓ auswählen · Tab übernehmen · Esc schließen</span><span>${state.treffer.length} von ${ALLE.length} Fragen</span></div>`:'';
 sendBtn.disabled=state.loading||!input.value.trim();
}
function uebernehmen(q){input.value=q;state.acZu=true;renderAc();input.focus({preventScroll:true})}
ac.addEventListener('mousedown',e=>{const b=e.target.closest('button');if(!b)return;e.preventDefault();uebernehmen(state.treffer[Number(b.dataset.kiAc)].q)});
input.addEventListener('input',()=>{state.acZu=false;state.acIndex=0;renderAc()});
input.addEventListener('focus',()=>{state.acZu=false;renderAc()});
input.addEventListener('blur',()=>setTimeout(()=>{state.acZu=true;renderAc()},150));
input.addEventListener('keydown',e=>{const n=state.treffer.length;
 if(n&&e.key==='ArrowDown'){e.preventDefault();state.acIndex=(state.acIndex+1)%n;renderAc()}
 else if(n&&e.key==='ArrowUp'){e.preventDefault();state.acIndex=(state.acIndex-1+n)%n;renderAc()}
 else if(n&&e.key==='Tab'){e.preventDefault();uebernehmen(state.treffer[state.acIndex].q)}
 else if(n&&e.key==='Escape'){state.acZu=true;renderAc()}
 else if(e.key==='Enter'){e.preventDefault();senden()}});
sendBtn.addEventListener('click',senden);

/* Chat */
function antwortHtml(text){
 const i=Math.max(text.lastIndexOf('— Basierend auf:'),text.lastIndexOf('— Wissensbasis:'));
 const haupt=i>0?text.slice(0,i).replace(/\s+$/,''):text;
 const fett=l=>esc(l).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>');
 return haupt.split('\n').map(l=>l.startsWith('## ')?`<div class="ki-h">${esc(l.slice(3))}</div>`:l.startsWith('- ')?`<div class="ki-li">• ${fett(l.slice(2))}</div>`:!l.trim()?'<div class="ki-gap"></div>':`<div>${fett(l)}</div>`).join('')}
function renderLog(){
 const chat=state.messages.length>0;sec.classList.toggle('ki-chat',chat);sec.classList.toggle('ki-busy',state.loading);log.hidden=!chat;resetBtn.hidden=!chat;
 log.innerHTML=state.messages.map((m,i)=>{const neu=i===state.neu?' neu':'';
  return m.role==='user'?`<div class="ki-msg user${neu}">${esc(m.content)}</div>`
   :`<div class="ki-row">${mark()}<div class="ki-msg${m.fehler?' fehler':''}${neu}">${antwortHtml(m.content)}</div></div>`}).join('')
  +(state.loading?`<div class="ki-wait" role="status">${mark(true)}InvestTimer liest die Daten …</div>`:'');
 log.scrollTop=log.scrollHeight;sendBtn.disabled=state.loading||!input.value.trim();
}
async function senden(){
 const frage=input.value.trim();if(!frage||state.loading)return;
 const verlauf=state.messages.slice(-MAX_VERLAUF).map(m=>({role:m.role,content:m.content}));
 state.messages.push({role:'user',content:frage});state.neu=state.messages.length-1;input.value='';state.acZu=true;state.loading=true;
 oeffneSheet();renderAc();renderLog();
 let antwort,fehler=false;
 try{
  const res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frage,verlauf})});
  if(res.status===429){antwort='Für heute ist das Fragenkontingent erreicht — morgen geht es weiter.';fehler=true}
  else if(!res.ok)throw new Error('HTTP '+res.status);
  else antwort=(await res.json()).antwort||'Leere Antwort erhalten.';
 }catch{antwort='Verbindung fehlgeschlagen — bitte in einem Moment erneut versuchen.';fehler=true}
 state.messages.push({role:'assistant',content:String(antwort),fehler});state.neu=state.messages.length-1;state.loading=false;renderLog();
}
resetBtn.addEventListener('click',()=>{if(state.loading)return;state.messages=[];state.neu=-1;schliesseSheet();renderLog();renderCards();input.focus({preventScroll:true})});

setzeWert(document.body.dataset.wert?Number(document.body.dataset.wert):null);
renderCards();renderAc();renderLog();
})();
