/* Verlauf des Marktstress im Detailbereich (angemeldet bzw. Premium). Eine durchgehende Linie.
   Stressphasen (historie/ereignisse.json) als dezente Baender; Desktop: Kurzname im Band, Hover/Klick zeigt die
   Ereigniskarte. Mobil (< 760 px): Baender ohne Beschriftung, darunter eine wischbare Leiste mit Chips. */
let verlauf=null,verlaufZeit=0,verlaufSpanne='1J',verlaufIndex=null,verlaufEreignis=null;
const vMobil=()=>window.matchMedia('(max-width:759px)').matches;
const panel=$('#details-panel');
const SPANNEN=[['1M',31,'taeglich'],['3M',92,'taeglich'],['1J',366,'taeglich'],['5J',1827,'woechentlich'],['A',0,'woechentlich']];
async function ladeVerlauf(){
 if(verlauf&&Date.now()-verlaufZeit<600000)return verlauf;
 try{verlauf=await api('historie')}catch(x){verlauf={fehler:x}}verlaufZeit=Date.now();return verlauf;
}
const vLang=()=>document.documentElement.lang==='en'?'en-GB':'de-DE';
const vMs=d=>Date.parse(d+'T12:00:00Z');
function vAuswahl(){
 const [,tage,art]=SPANNEN.find(s=>s[0]===verlaufSpanne)||SPANNEN[2],reihe=verlauf[art]||[];
 const ende=reihe.length?vMs(reihe[reihe.length-1][0]):Date.now(),start=tage?ende-tage*864e5:-Infinity;
 const p=reihe.filter(x=>vMs(x[0])>=start);
 const a=p.length?p[0][0]:'',b=p.length?p[p.length-1][0]:'';
 const e=(verlauf.ereignisse||[]).filter(x=>x.ende>a&&x.start<=b);
 return {p,e,art};
}
function vDatum(d,kurz){const o=kurz?(verlaufSpanne==='5J'||verlaufSpanne==='A'?{month:'short',year:'numeric'}:{day:'numeric',month:'short'}):{day:'numeric',month:'long',year:'numeric'};
 return new Date(vMs(d)).toLocaleDateString(vLang(),Object.assign({timeZone:'UTC'},o))}
let vW=600;const vL=34,vR=10;
const vBreite=()=>{const b=panel&&panel.querySelector('.verlauf');vW=Math.round(Math.min(600,Math.max(280,b&&b.clientWidth||600)))};
function vX(p){const a=vMs(p[0][0]),b=vMs(p[p.length-1][0]);return d=>vL+(b===a?(vW-vL-vR)/2:(vMs(d)-a)/(b-a)*(vW-vL-vR))}
const vEn=()=>document.documentElement.lang==='en';
function stressSvg(p,x,e){
 const H=180,T=10,B=24,y=w=>T+(100-w)*(H-T-B)/100,mobil=vW<480;
 let s='<svg class="chart-svg verlauf-svg" data-panel="stress" viewBox="0 0 '+vW+' '+H+'" aria-hidden="true">';
 for(const g of [0,25,50,75,100])s+='<line class="chart-grid" x1="'+vL+'" x2="'+(vW-vR)+'" y1="'+y(g)+'" y2="'+y(g)+'"/><text class="chart-text" x="0" y="'+(y(g)+4)+'">'+g+'</text>';
 /* Stressphasen als Baender; Kurzname nur auf dem Desktop, ohne Ueberlappung (bis drei Zeilen) */
 const reihen=[[],[],[]],aktiv=vAktivId(e);
 (e||[]).forEach(m=>{const x0=Math.max(vL,x(m.start)),x1=Math.min(vW-vR,x(m.ende)),bx=Math.max(x1-x0,2);
  s+='<rect class="verlauf-band'+(m.id===aktiv?' aktiv':'')+'" data-band="'+m.id+'" x="'+x0.toFixed(1)+'" y="'+T+'" width="'+bx.toFixed(1)+'" height="'+(H-T-B)+'"/>';
  if(!vMobil()){const name=vEn()?m.kurz_en:m.kurz,breite=name.length*5.4+6,a=x0+2,b=a+breite;
   if(b<=vW-vR+2){const r=reihen.findIndex(z=>z.every(([u,v])=>b<u-2||a>v+2));
    if(r>=0){reihen[r].push([a,b]);s+='<text class="verlauf-band-text" x="'+(x0+3).toFixed(1)+'" y="'+(T+10+r*12)+'">'+esc(name)+'</text>'}}}
 });
 s+='<polyline class="chart-line" points="'+p.map(q=>x(q[0]).toFixed(1)+','+y(q[1]).toFixed(1)).join(' ')+'"/>';
 const z=p[p.length-1];
 s+='<circle class="chart-point" r="4.5" cx="'+x(z[0])+'" cy="'+y(z[1])+'"/><text class="chart-label" text-anchor="end" x="'+(x(z[0])-8)+'" y="'+(y(z[1])-9)+'">'+z[1]+'</text>';
 s+='<text class="chart-text" x="'+vL+'" y="'+(H-5)+'">'+vDatum(p[0][0],1)+'</text><text class="chart-text" text-anchor="end" x="'+(vW-vR)+'" y="'+(H-5)+'">'+vDatum(z[0],1)+'</text>';
 s+='<line class="verlauf-cursor" y1="'+T+'" y2="'+(H-B)+'" x1="0" x2="0" visibility="hidden"/><circle class="verlauf-cursor-punkt" r="4" cx="0" cy="0" visibility="hidden"/></svg>';
 return s;
}
function verlaufHtml(){
 const v=verlauf;vBreite();
 if(!v)return '<p class="chart-note">'+t('alarmLaedt')+'</p>';
 if(v.fehler==='premium')return '<p class="chart-note">'+t('verlaufPremium')+'</p><button type="button" class="primary" id="verlauf-premium">'+t('premiumAnsehen')+'</button>';
 if(v.fehler||!(v.taeglich||[]).length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const {p,e}=vAuswahl();if(!p.length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const x=vX(p),aktiv=vAktivId(e),H=180,T=10,B=24;
 const knoepfe=SPANNEN.map(([k])=>'<button type="button" class="verlauf-spanne'+(k===verlaufSpanne?' aktiv':'')+'" data-spanne="'+k+'" aria-pressed="'+(k===verlaufSpanne)+'">'+(k==='A'?t('verlaufAlle'):k==='1J'?t('verlauf1J'):k==='5J'?t('verlauf5J'):k)+'</button>').join('');
 const name=m=>vEn()?m.name_en:m.name;
 /* Desktop: unsichtbare Schaltflaechen ueber den Baendern (Tab, Enter, Hover); mobil: Chips */
 const baender=vMobil()?'':'<div class="verlauf-baender">'+e.map(m=>{const x0=Math.max(vL,x(m.start)),x1=Math.min(vW-vR,x(m.ende)),bx=Math.max(x1-x0,6);
  return '<button type="button" class="verlauf-band-knopf" data-ereignis="'+m.id+'" aria-pressed="'+(m.id===aktiv)+'" aria-label="'+esc(name(m)+', '+vZeitraum(m))+'" style="left:'+(x0/vW*100).toFixed(2)+'%;width:'+(bx/vW*100).toFixed(2)+'%;top:'+(T/H*100).toFixed(2)+'%;height:'+((H-T-B)/H*100).toFixed(2)+'%"></button>'}).join('')+'</div>';
 const chips=vMobil()&&e.length?'<div class="verlauf-chips" role="group" aria-label="'+t('ereignisseLabel')+'">'+e.slice().reverse().map(m=>'<button type="button" class="verlauf-chip" data-ereignis="'+m.id+'" aria-pressed="'+(m.id===aktiv)+'">'+esc(vEn()?m.kurz_en:m.kurz)+' · '+m.spitze.w+'</button>').join('')+'</div>':'';
 return '<div class="verlauf-kopf"><div class="verlauf-knoepfe" role="group" aria-label="'+t('verlaufSpanne')+'">'+knoepfe+'</div></div>'
  +'<div class="verlauf-diagramm" tabindex="0" role="group" aria-label="'+esc(t('verlaufAria').replace('{n}',p.length))+'">'
  +stressSvg(p,x,e)+baender
  +'<div class="verlauf-tip" role="status" aria-live="polite" hidden></div></div>'
  +chips+'<div class="ereignis-karte" aria-live="polite"'+(aktiv?'':' hidden')+'>'+vKarte(e.find(m=>m.id===aktiv))+'</div>'
  +'<p class="chart-note">'+t('verlaufHinweis')+' '+t('verlaufEreignisHinweis')+'</p>';
}
/* Aktives Ereignis: gewaehltes, wenn sichtbar; sonst das juengste im sichtbaren Zeitraum */
function vAktivId(e){if(!e||!e.length)return null;if(verlaufEreignis&&e.some(m=>m.id===verlaufEreignis))return verlaufEreignis;return e[e.length-1].id}
function vMonat(d){return new Date(vMs(d)).toLocaleDateString(vLang(),{month:'short',year:'numeric',timeZone:'UTC'})}
function vZeitraum(m){const ende=new Date(vMs(m.ende)-864e5).toISOString().slice(0,10),a=vMonat(m.start),b=vMonat(ende);return a===b?a:a+' – '+b}
function vKarte(m){
 if(!m)return '';
 const nm=vEn()?m.name_en:m.name,txt=vEn()?m.text_en:m.text,bl=m.bloecke||{};
 const zeile=(k,l)=>bl[k]==null?'':'<div class="trieb-zeile"><span>'+esc(t(l))+'</span><span class="trieb-balken" aria-hidden="true"><i style="width:'+Math.round(bl[k])+'%"></i></span><b>'+Math.round(bl[k])+'</b></div>';
 return '<h4>'+esc(nm)+'</h4><p class="karte-zeit">'+esc(vZeitraum(m))+'</p>'
  +'<dl class="karte-zahlen"><div><dt>'+t('karteHoechst')+'</dt><dd>'+t('karteAm').replace('{w}',m.spitze.w).replace('{d}',vDatum(m.spitze.d))+'</dd></div>'
  +'<div><dt>'+t('karteUnter40')+'</dt><dd>'+(m.unter40?t('karteNachTagen').replace('{n}',m.unter40.tage):t('karteNochNicht'))+'</dd></div></dl>'
  +(m.bloecke?'<p class="karte-trieb-titel">'+t('karteTrieb').replace('{d}',vDatum(m.spitze.d))+'</p>'+zeile('volatility','triebVol')+zeile('price','triebPreis')+zeile('positioning','triebStimmung'):'')
  +(txt?'<p class="karte-text">'+esc(txt)+'</p>':'');
}
function vAktiviere(id){
 verlaufEreignis=id;const box=panel.querySelector('.verlauf');if(!box)return;const {e}=vAuswahl(),m=e.find(x=>x.id===id);if(!m)return;
 box.querySelectorAll('[data-band]').forEach(r=>r.classList.toggle('aktiv',r.dataset.band===id));
 box.querySelectorAll('[data-ereignis]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.ereignis===id)));
 const k=box.querySelector('.ereignis-karte');if(k){k.innerHTML=vKarte(m);k.hidden=false}
}
function vTitel(){return t('verlaufTitel')}
function vZeichnen(fokus){
 const box=panel&&panel.querySelector('.verlauf');if(!box)return;
 box.innerHTML='<h3>'+vTitel()+'</h3>'+verlaufHtml();verlaufIndex=null;
 if(fokus)box.querySelector(fokus)?.focus();
}
/* Tooltip: naechster Tag zur Zeigerposition bzw. per Pfeiltasten */
function vZeige(i){
 const box=panel.querySelector('.verlauf'),dia=box&&box.querySelector('.verlauf-diagramm');if(!dia)return;
 const {p}=vAuswahl();if(!p.length)return;i=Math.max(0,Math.min(p.length-1,i));verlaufIndex=i;
 const q=p[i],x=vX(p)(q[0]),svg=dia.querySelector('[data-panel=stress]'),H=180,T=10,B=24,yy=T+(100-q[1])*(H-T-B)/100;
 dia.querySelectorAll('.verlauf-cursor').forEach(l=>{l.setAttribute('x1',x);l.setAttribute('x2',x);l.setAttribute('visibility','visible')});
 const c=dia.querySelector('.verlauf-cursor-punkt');c.setAttribute('cx',x);c.setAttribute('cy',yy);c.setAttribute('visibility','visible');
 const tip=dia.querySelector('.verlauf-tip');
 tip.innerHTML='<b>'+vDatum(q[0])+'</b><span>'+t('tipWert').replace('{w}',q[1])+'</span><span>'+t('tipBestandteile').replace('{n}',q[2]==null?'–':q[2])+'</span><span class="'+(q[3]==='a'?'':'tip-rueck')+'">'+t(q[3]==='a'?'legendeAuf':'legendeRueck')+'</span>';
 tip.hidden=false;
 const r=svg.getBoundingClientRect(),d=dia.getBoundingClientRect(),px=r.left-d.left+x/vW*r.width;
 tip.style.left=Math.max(0,Math.min(d.width-tip.offsetWidth,px-tip.offsetWidth/2))+'px';
}
function vVerberge(){const dia=panel.querySelector('.verlauf-diagramm');if(!dia)return;dia.querySelector('.verlauf-tip').hidden=true;dia.querySelectorAll('.verlauf-cursor,.verlauf-cursor-punkt').forEach(l=>l.setAttribute('visibility','hidden'))}
function vIndexBei(ev){
 const dia=ev.target.closest('.verlauf-diagramm'),svg=dia&&dia.querySelector('[data-panel=stress]');if(!svg)return null;
 const r=svg.getBoundingClientRect(),xv=(ev.clientX-r.left)/r.width*vW,{p}=vAuswahl(),x=vX(p);
 let best=0,bd=Infinity;p.forEach((q,i)=>{const d=Math.abs(x(q[0])-xv);if(d<bd){bd=d;best=i}});return best;
}
async function zeigeVerlauf(){
 if(!panel||panel.hidden||!(IT.session||IT.member))return;
 let box=panel.querySelector('.verlauf');
 if(!box){box=document.createElement('section');box.className='verlauf';const intro=panel.querySelector('.detail-intro');if(!intro)return;intro.after(box)}
 box.innerHTML='<h3>'+vTitel()+'</h3>'+verlaufHtml();
 if(!verlauf){await ladeVerlauf();vZeichnen()}
}
if(panel){
 new MutationObserver(()=>{if(!panel.querySelector('.verlauf'))zeigeVerlauf()}).observe(panel,{childList:true,attributes:true,attributeFilter:['hidden']});
 panel.addEventListener('click',e=>{const ev=e.target.closest('[data-ereignis]');if(ev){vAktiviere(ev.dataset.ereignis);return}
  const b=e.target.closest('[data-spanne],#verlauf-premium');if(!b)return;
  if(b.id==='verlauf-premium'){IT.oeffneKonto&&IT.oeffneKonto(b,'paywall');return}
  verlaufSpanne=b.dataset.spanne;vZeichnen('[data-spanne="'+verlaufSpanne+'"]')});
 panel.addEventListener('pointerover',e=>{const b=e.target.closest('.verlauf-band-knopf');if(b&&e.pointerType==='mouse')vAktiviere(b.dataset.ereignis)});
 panel.addEventListener('pointermove',e=>{if(!e.target.closest('.verlauf-diagramm'))return;const i=vIndexBei(e);if(i!=null)vZeige(i)});
 panel.addEventListener('pointerdown',e=>{if(!e.target.closest('.verlauf-diagramm'))return;const i=vIndexBei(e);if(i!=null)vZeige(i)});
 panel.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse'&&e.target.classList&&e.target.classList.contains('verlauf-diagramm'))vVerberge()},true);
 panel.addEventListener('keydown',e=>{if(!e.target.classList||!e.target.classList.contains('verlauf-diagramm'))return;
  const n=vAuswahl().p.length;let i=verlaufIndex==null?n-1:verlaufIndex;
  if(e.key==='ArrowLeft')i--;else if(e.key==='ArrowRight')i++;else if(e.key==='Home')i=0;else if(e.key==='End')i=n-1;else if(e.key==='Escape'){vVerberge();return}else return;
  e.preventDefault();vZeige(i)});
 panel.addEventListener('focusin',e=>{if(e.target.classList&&e.target.classList.contains('verlauf-diagramm'))vZeige(verlaufIndex==null?vAuswahl().p.length-1:verlaufIndex)});
 panel.addEventListener('focusout',e=>{if(e.target.classList&&e.target.classList.contains('verlauf-diagramm'))vVerberge()});
}
let vGroesse=null;window.addEventListener('resize',()=>{clearTimeout(vGroesse);vGroesse=setTimeout(()=>{if(verlauf&&panel&&panel.querySelector('.verlauf-diagramm')){const alt=vW,altM=panel.querySelector('.verlauf-chips')!=null;vBreite();if(alt!==vW||altM!==vMobil())vZeichnen()}},150)});
document.addEventListener('investtimer:update',()=>{verlauf=null;const b=panel&&panel.querySelector('.verlauf');if(b)b.remove();zeigeVerlauf()});
new MutationObserver(()=>{if(verlauf&&panel&&panel.querySelector('.verlauf'))vZeichnen()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
