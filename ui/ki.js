(() => {
/* 05 · InvestTimer KI: Fragenkarten, Autocomplete, Chat. Sichtbar nur, wenn /api/chat erreichbar ist. */
'use strict';
const KATS=__KI_KATEGORIEN__;
const API='/api/chat',PRO_SEITE=3,MAX_VERLAUF=6;
const $=s=>document.querySelector(s);
const sec=$('#ki'),openBtn=$('#ki-open'),input=$('#ki-input'),sendBtn=$('#ki-send'),log=$('#ki-log'),ac=$('#ki-ac'),cards=$('#ki-cards'),composer=$('#ki-composer'),resetBtn=$('#ki-reset');
if(!sec||!input)return;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const seiten=k=>Math.ceil(k.fragen.length/PRO_SEITE);
const ALLE=KATS.flatMap(k=>k.fragen.map(q=>({q,kat:k.kurz.toUpperCase()})));
const state={messages:[],loading:false,available:false,seite:KATS.map(k=>Math.floor(Math.random()*seiten(k))),kat:0,acIndex:0,acZu:true,treffer:[]};
const ICON={
 gauge:'<path d="M4 17a8 8 0 0 1 16 0"/><path d="m12 17-3.5-5.5"/>',
 activity:'<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
 bars:'<line x1="6" y1="20" x2="6" y2="11"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="18" y1="20" x2="18" y2="14"/>',
 rotate:'<path d="M21 12a9 9 0 1 1-2.6-6.4"/><polyline points="21 3 21 8 16 8"/>'
};
const icon=n=>`<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[n]||''}</svg>`;

/* Sichtbarkeit: nur mit erreichbarem Backend und in der deutschen Ansicht */
function syncVisible(){const show=state.available&&document.documentElement.lang!=='en';sec.hidden=!show;if(openBtn)openBtn.hidden=!show}
new MutationObserver(syncVisible).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
if(location.protocol.startsWith('http'))fetch(API,{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{state.available=!!(d&&d.ok);syncVisible()}).catch(()=>{});
if(openBtn)openBtn.addEventListener('click',()=>{sec.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});input.focus({preventScroll:true})});

/* Fragenkarten */
function renderCards(){
 cards.innerHTML=`<div class="ki-tabs" role="tablist" aria-label="Kategorien">${KATS.map((k,i)=>`<button type="button" role="tab" aria-selected="${i===state.kat}" data-ki-tab="${i}">${esc(k.kurz)}</button>`).join('')}</div><div class="ki-grid">${KATS.map((k,i)=>{
  const s=state.seite[i],n=seiten(k),fragen=k.fragen.slice(s*PRO_SEITE,s*PRO_SEITE+PRO_SEITE);
  return `<div class="ki-card${i===state.kat?' on':''}"><div class="ki-card-top"><span>${icon(k.icon)}${esc(k.label)}</span>${n>1?`<button type="button" class="ki-shuffle" data-ki-shuffle="${i}" aria-label="Andere Fragen zu ${esc(k.kurz)} zeigen" title="Andere Fragen">${icon('rotate')}</button>`:''}</div>${fragen.map(q=>`<button type="button" class="ki-q" data-ki-q="${esc(q)}">${esc(q)}</button>`).join('')}<div class="ki-dots" aria-hidden="true">${n>1?Array.from({length:n},(_,j)=>`<i${j===s?' class="on"':''}></i>`).join(''):''}</div></div>`}).join('')}</div>`;
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
 const chat=state.messages.length>0;sec.classList.toggle('ki-chat',chat);log.hidden=!chat;resetBtn.hidden=!chat;
 log.innerHTML=state.messages.map(m=>m.role==='user'?`<div class="ki-msg user">${esc(m.content)}</div>`:`<div class="ki-msg">${antwortHtml(m.content)}</div>`).join('')+(state.loading?'<div class="ki-wait"><i></i>InvestTimer liest die Daten …</div>':'');
 log.scrollTop=log.scrollHeight;sendBtn.disabled=state.loading||!input.value.trim();
}
async function senden(){
 const frage=input.value.trim();if(!frage||state.loading)return;
 const verlauf=state.messages.slice(-MAX_VERLAUF).map(m=>({role:m.role,content:m.content}));
 state.messages.push({role:'user',content:frage});input.value='';state.acZu=true;state.loading=true;renderAc();renderLog();
 let antwort;
 try{
  const res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frage,verlauf})});
  if(res.status===429)antwort='Für heute ist das Fragenkontingent erreicht — morgen geht es weiter.';
  else if(!res.ok)throw new Error('HTTP '+res.status);
  else antwort=(await res.json()).antwort||'Leere Antwort erhalten.';
 }catch{antwort='Verbindung fehlgeschlagen — bitte in einem Moment erneut versuchen.'}
 state.messages.push({role:'assistant',content:String(antwort)});state.loading=false;renderLog();
}
resetBtn.addEventListener('click',()=>{if(state.loading)return;state.messages=[];renderLog();renderCards();input.focus({preventScroll:true})});

/* Rotierende Kugel (92 Punkte, Fibonacci-Sphaere). Laeuft nur, solange sie sichtbar ist. */
const canvas=$('#ki-canvas'),ctx=canvas.getContext('2d');
const nodes=Array.from({length:92},(_,i)=>{const y=1-i/91*2,r=Math.sqrt(1-y*y),a=i*2.39996;return {x:Math.cos(a)*r,y,z:Math.sin(a)*r}});
const edges=[];nodes.forEach((a,i)=>nodes.forEach((b,j)=>{if(j>i&&Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z)<0.45)edges.push([i,j])}));
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches,TAU=Math.PI*2;
let w=0,h=0,time=0,prev=0,raf=0,inView=false;
function draw(){
 if(!w||!h)return;ctx.clearRect(0,0,w,h);
 const cx=w*0.5,cy=h*0.44,r=Math.min(w*0.19,h*0.34),angle=time*0.11,tilt=0.2;
 const glow=ctx.createRadialGradient(cx,cy,0,cx,cy,r*1.7);glow.addColorStop(0,'rgba(46,109,92,0.10)');glow.addColorStop(1,'rgba(46,109,92,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
 const ps=nodes.map(p=>{const x=p.x*Math.cos(angle)+p.z*Math.sin(angle),z=-p.x*Math.sin(angle)+p.z*Math.cos(angle),y=p.y*Math.cos(tilt)-z*Math.sin(tilt),zz=p.y*Math.sin(tilt)+z*Math.cos(tilt),sc=1+zz*0.12;return {x:cx+x*r*sc,y:cy+y*r*sc,z:zz}});
 edges.forEach(([i,j],n)=>{const a=ps[i],b=ps[j],al=0.08+((a.z+b.z+2)/4)*0.3;
  ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=`rgba(46,109,92,${al})`;ctx.lineWidth=0.65;ctx.stroke();
  if(n%29===0){const p=(time*0.15+n*0.079)%1;ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*p,a.y+(b.y-a.y)*p,1.35,0,TAU);ctx.fillStyle='#9b6f32';ctx.fill()}});
 ps.slice().sort((a,b)=>a.z-b.z).forEach(p=>{ctx.beginPath();ctx.arc(p.x,p.y,0.65+(p.z+1)*0.55,0,TAU);ctx.fillStyle=`rgba(27,74,62,${(p.z+1)*0.3+0.2})`;ctx.fill()});
 ctx.save();ctx.translate(cx,cy);ctx.strokeStyle='rgba(46,109,92,0.16)';ctx.lineWidth=0.7;ctx.beginPath();ctx.ellipse(0,r*0.95,r*1.15,r*0.11,0,0,TAU);ctx.stroke();ctx.restore();
}
function frame(ms){const dt=Math.min((ms-prev)/1000,0.05);prev=ms;if(!document.hidden&&!reduce)time+=dt;draw();raf=inView&&!reduce?requestAnimationFrame(frame):0}
new ResizeObserver(()=>{const r=canvas.getBoundingClientRect();if(!r.width||!r.height)return;w=r.width;h=r.height;const d=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);ctx.setTransform(d,0,0,d,0,0);draw()}).observe(canvas);
new IntersectionObserver(es=>{inView=es[0].isIntersecting;if(inView&&!raf&&!reduce){prev=performance.now();raf=requestAnimationFrame(frame)}}).observe(canvas);

renderCards();renderAc();renderLog();
})();
