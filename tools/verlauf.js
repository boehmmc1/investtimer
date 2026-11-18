/* Verlauf des Marktstress im Detailbereich (angemeldet bzw. Premium).
   Aufgezeichnet (ab 15.11.2026) durchgezogen, zurueckgerechnet heller und gestrichelt. Optional: S&P 500 als
   eigenes Panel mit gemeinsamer Zeitachse (nur wenn die API ihn liefert: Schalter IT_SPX_VERGLEICH). */
let verlauf=null,verlaufZeit=0,verlaufSpanne='1J',verlaufIndex=null;
let spxAn=false;try{spxAn=localStorage.getItem('investtimer-spx')==='1'}catch{}
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
 let s=[];if(verlauf.spx&&spxAn){const r=verlauf.spx[art]||[];const a=p.length?vMs(p[0][0]):start;s=r.filter(x=>vMs(x[0])>=a&&vMs(x[0])<=ende)}
 return {p,s,art};
}
function vDatum(d,kurz){const o=kurz?(verlaufSpanne==='5J'||verlaufSpanne==='A'?{month:'short',year:'numeric'}:{day:'numeric',month:'short'}):{day:'numeric',month:'long',year:'numeric'};
 return new Date(vMs(d)).toLocaleDateString(vLang(),Object.assign({timeZone:'UTC'},o))}
let vW=600;const vL=34,vR=10;
const vBreite=()=>{const b=panel&&panel.querySelector('.verlauf');vW=Math.round(Math.min(600,Math.max(280,b&&b.clientWidth||600)))};
function vX(p){const a=vMs(p[0][0]),b=vMs(p[p.length-1][0]);return d=>vL+(b===a?(vW-vL-vR)/2:(vMs(d)-a)/(b-a)*(vW-vL-vR))}
function stressSvg(p,x){
 const H=180,T=10,B=24,y=w=>T+(100-w)*(H-T-B)/100;
 let s='<svg class="chart-svg verlauf-svg" data-panel="stress" viewBox="0 0 '+vW+' '+H+'" aria-hidden="true">';
 for(const g of [0,25,50,75,100])s+='<line class="chart-grid" x1="'+vL+'" x2="'+(vW-vR)+'" y1="'+y(g)+'" y2="'+y(g)+'"/><text class="chart-text" x="0" y="'+(y(g)+4)+'">'+g+'</text>';
 /* Abschnitte je Herkunft; am Uebergang verbunden */
 let seg=[],art=null;const fertig=()=>{if(seg.length>1)s+='<polyline class="'+(art==='a'?'chart-line':'chart-line verlauf-rueck')+'" points="'+seg.join(' ')+'"/>';};
 p.forEach((q,i)=>{const pt=x(q[0]).toFixed(1)+','+y(q[1]).toFixed(1);if(q[3]!==art){fertig();seg=i?[seg[seg.length-1]]:[];art=q[3]}seg.push(pt)});fertig();
 const z=p[p.length-1];
 s+='<circle class="chart-point" r="4.5" cx="'+x(z[0])+'" cy="'+y(z[1])+'"/><text class="chart-label" text-anchor="end" x="'+(x(z[0])-8)+'" y="'+(y(z[1])-9)+'">'+z[1]+'</text>';
 s+='<text class="chart-text" x="'+vL+'" y="'+(H-5)+'">'+vDatum(p[0][0],1)+'</text><text class="chart-text" text-anchor="end" x="'+(vW-vR)+'" y="'+(H-5)+'">'+vDatum(z[0],1)+'</text>';
 s+='<line class="verlauf-cursor" y1="'+T+'" y2="'+(H-B)+'" x1="-10" x2="-10"/><circle class="verlauf-cursor-punkt" r="4" cx="-10" cy="-10"/></svg>';
 return s;
}
function spxSvg(s,x){
 if(s.length<2)return '';
 const H=130,T=8,B=8,log=['1J','5J','A'].includes(verlaufSpanne),f=v=>log?Math.log(v):v,fi=v=>log?Math.exp(v):v;
 const lo=Math.min(...s.map(q=>q[1])),hi=Math.max(...s.map(q=>q[1])),a=f(lo),b=f(hi),pad=(b-a)*.08||1;
 const y=v=>T+(b+pad-f(v))*(H-T-B)/((b+pad)-(a-pad));
 const zahl=v=>v>=10000?Math.round(v/1000)+'k':Math.round(v).toLocaleString(vLang());
 let o='<svg class="chart-svg verlauf-svg verlauf-spx-svg" data-panel="spx" viewBox="0 0 '+vW+' '+H+'" aria-hidden="true">';
 for(const v of [lo,fi((a+b)/2),hi])o+='<line class="chart-grid" x1="'+vL+'" x2="'+(vW-vR)+'" y1="'+y(v)+'" y2="'+y(v)+'"/><text class="chart-text" x="0" y="'+(y(v)+4)+'">'+zahl(v)+'</text>';
 o+='<polyline class="verlauf-spx-linie" points="'+s.map(q=>x(q[0]).toFixed(1)+','+y(q[1]).toFixed(1)).join(' ')+'"/>';
 o+='<line class="verlauf-cursor" y1="'+T+'" y2="'+(H-B)+'" x1="-10" x2="-10"/></svg>';
 return o;
}
function verlaufHtml(){
 const v=verlauf;vBreite();
 if(!v)return '<p class="chart-note">'+t('alarmLaedt')+'</p>';
 if(v.fehler==='premium')return '<p class="chart-note">'+t('verlaufPremium')+'</p><button type="button" class="primary" id="verlauf-premium">'+t('premiumAnsehen')+'</button>';
 if(v.fehler||!(v.taeglich||[]).length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const {p,s}=vAuswahl();if(!p.length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const x=vX(p),hatR=p.some(q=>q[3]==='r'),hatA=p.some(q=>q[3]==='a'),spx=!!(v.spx&&spxAn&&s.length>1);
 const knoepfe=SPANNEN.map(([k])=>'<button type="button" class="verlauf-spanne'+(k===verlaufSpanne?' aktiv':'')+'" data-spanne="'+k+'" aria-pressed="'+(k===verlaufSpanne)+'">'+(k==='A'?t('verlaufAlle'):k==='1J'?t('verlauf1J'):k==='5J'?t('verlauf5J'):k)+'</button>').join('');
 const legende='<div class="verlauf-legende">'+(hatA?'<span><i class="voll"></i>'+t('legendeAuf')+'</span>':'')+(hatR?'<span><i class="gestrichelt"></i>'+t('legendeRueck')+'</span>':'')+'</div>';
 const schalter=v.spx?'<label class="verlauf-spx-schalter"><input type="checkbox" id="verlauf-spx"'+(spxAn?' checked':'')+'> '+t('spxEinblenden')+'</label>':'';
 return '<div class="verlauf-kopf"><div class="verlauf-knoepfe" role="group" aria-label="'+t('verlaufSpanne')+'">'+knoepfe+'</div>'+schalter+'</div>'
  +legende
  +'<div class="verlauf-diagramm" tabindex="0" role="group" aria-label="'+esc(t('verlaufAria').replace('{n}',p.length))+'">'
  +stressSvg(p,x)+(spx?'<p class="verlauf-panel-titel">'+t('spxLabel')+(['1J','5J','A'].includes(verlaufSpanne)?' · '+t('spxLog'):'')+'</p>'+spxSvg(s,x):'')
  +'<div class="verlauf-tip" role="status" aria-live="polite" hidden></div></div>'
  +'<p class="chart-note">'+t('verlaufHinweis')+'</p>'+(spx?'<p class="chart-note">'+esc(t('spxQuelle'))+'</p>':'');
}
function vTitel(){return verlauf&&verlauf.spx&&spxAn?t('verlaufTitelSpx'):t('verlaufTitel')}
function vZeichnen(fokus){
 const box=panel&&panel.querySelector('.verlauf');if(!box)return;
 box.innerHTML='<h3>'+vTitel()+'</h3>'+verlaufHtml();verlaufIndex=null;
 if(fokus)box.querySelector(fokus)?.focus();
}
/* Tooltip: naechster Tag zur Zeigerposition bzw. per Pfeiltasten */
function vZeige(i){
 const box=panel.querySelector('.verlauf'),dia=box&&box.querySelector('.verlauf-diagramm');if(!dia)return;
 const {p,s}=vAuswahl();if(!p.length)return;i=Math.max(0,Math.min(p.length-1,i));verlaufIndex=i;
 const q=p[i],x=vX(p)(q[0]),svg=dia.querySelector('[data-panel=stress]'),H=180,T=10,B=24,yy=T+(100-q[1])*(H-T-B)/100;
 dia.querySelectorAll('.verlauf-cursor').forEach(l=>{l.setAttribute('x1',x);l.setAttribute('x2',x)});
 const c=dia.querySelector('.verlauf-cursor-punkt');c.setAttribute('cx',x);c.setAttribute('cy',yy);
 let sp='';if(s.length&&dia.querySelector('[data-panel=spx]')){let k=null;for(const z of s){if(z[0]<=q[0])k=z;else break}if(k)sp='<span>'+t('spxLabel')+' '+Math.round(k[1]).toLocaleString(vLang())+'</span>'}
 const tip=dia.querySelector('.verlauf-tip');
 tip.innerHTML='<b>'+vDatum(q[0])+'</b><span>'+t('tipWert').replace('{w}',q[1])+'</span><span>'+t('tipBestandteile').replace('{n}',q[2]==null?'–':q[2])+'</span><span class="'+(q[3]==='a'?'':'tip-rueck')+'">'+t(q[3]==='a'?'legendeAuf':'legendeRueck')+'</span>'+sp;
 tip.hidden=false;
 const r=svg.getBoundingClientRect(),d=dia.getBoundingClientRect(),px=r.left-d.left+x/vW*r.width;
 tip.style.left=Math.max(0,Math.min(d.width-tip.offsetWidth,px-tip.offsetWidth/2))+'px';
}
function vVerberge(){const dia=panel.querySelector('.verlauf-diagramm');if(!dia)return;dia.querySelector('.verlauf-tip').hidden=true;dia.querySelectorAll('.verlauf-cursor').forEach(l=>{l.setAttribute('x1',-10);l.setAttribute('x2',-10)});const c=dia.querySelector('.verlauf-cursor-punkt');c&&c.setAttribute('cx',-10)}
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
 panel.addEventListener('click',e=>{const b=e.target.closest('[data-spanne],#verlauf-premium');if(!b)return;
  if(b.id==='verlauf-premium'){IT.oeffneKonto&&IT.oeffneKonto(b,'paywall');return}
  verlaufSpanne=b.dataset.spanne;vZeichnen('[data-spanne="'+verlaufSpanne+'"]')});
 panel.addEventListener('change',e=>{if(e.target.id!=='verlauf-spx')return;spxAn=e.target.checked;try{localStorage.setItem('investtimer-spx',spxAn?'1':'0')}catch{}vZeichnen('#verlauf-spx')});
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
let vGroesse=null;window.addEventListener('resize',()=>{clearTimeout(vGroesse);vGroesse=setTimeout(()=>{if(verlauf&&panel&&panel.querySelector('.verlauf-diagramm')){const alt=vW;vBreite();if(alt!==vW)vZeichnen()}},150)});
document.addEventListener('investtimer:update',()=>{verlauf=null;const b=panel&&panel.querySelector('.verlauf');if(b)b.remove();zeigeVerlauf()});
new MutationObserver(()=>{if(verlauf&&panel&&panel.querySelector('.verlauf'))vZeichnen()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
