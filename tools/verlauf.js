/* Verlauf des Marktstress (Tageswerte) im Detailbereich, fuer angemeldete bzw. Premium-Nutzer */
let verlauf=null,verlaufZeit=0,verlaufSpanne=90;
const panel=$('#details-panel');
async function ladeVerlauf(){
 if(verlauf&&Date.now()-verlaufZeit<600000)return verlauf;
 try{verlauf=await api('historie')}catch(x){verlauf={fehler:x}}verlaufZeit=Date.now();return verlauf;
}
function verlaufSvg(p){
 const W=600,H=170,L=28,R=12,T=10,B=24,x=i=>L+(p.length<2?(W-L-R)/2:i*(W-L-R)/(p.length-1)),y=w=>T+(100-w)*(H-T-B)/100;
 const fmt=d=>new Date(d+'T12:00:00').toLocaleDateString(document.documentElement.lang==='en'?'en-GB':'de-DE',{day:'numeric',month:'short'});
 let s='<svg class="chart-svg verlauf-svg" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+t('verlaufAria').replace('{n}',p.length)+'">';
 for(const g of [0,25,50,75,100])s+='<line class="chart-grid" x1="'+L+'" x2="'+(W-R)+'" y1="'+y(g)+'" y2="'+y(g)+'"/><text class="chart-text" x="0" y="'+(y(g)+4)+'">'+g+'</text>';
 if(p.length>1)s+='<polyline class="chart-line" points="'+p.map((q,i)=>x(i).toFixed(1)+','+y(q.w).toFixed(1)).join(' ')+'"/>';
 const z=p[p.length-1];
 s+='<circle class="chart-point" r="5" cx="'+x(p.length-1)+'" cy="'+y(z.w)+'"/><text class="chart-label" text-anchor="end" x="'+(x(p.length-1)-8)+'" y="'+(y(z.w)-10)+'">'+z.w+'</text>';
 s+='<text class="chart-text" x="'+L+'" y="'+(H-4)+'">'+fmt(p[0].d)+'</text><text class="chart-text" text-anchor="end" x="'+(W-R)+'" y="'+(H-4)+'">'+fmt(z.d)+'</text></svg>';
 return s;
}
function verlaufHtml(){
 const v=verlauf;
 if(!v)return '<p class="chart-note">'+t('alarmLaedt')+'</p>';
 if(v.fehler==='premium')return '<p class="chart-note">'+t('verlaufPremium')+'</p><button type="button" class="primary" id="verlauf-premium">'+t('premiumAnsehen')+'</button>';
 if(v.fehler||!v.punkte||!v.punkte.length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const alle=v.punkte,p=verlaufSpanne?alle.slice(-verlaufSpanne):alle;
 const knoepfe=[[30,'1M'],[90,'3M'],[365,'1J'],[0,t('verlaufAlle')]].map(([n,l])=>'<button type="button" class="verlauf-spanne'+(n===verlaufSpanne?' aktiv':'')+'" data-spanne="'+n+'" aria-pressed="'+(n===verlaufSpanne)+'">'+l+'</button>').join('');
 const min=Math.min(...p.map(q=>q.w)),max=Math.max(...p.map(q=>q.w));
 return '<div class="verlauf-knoepfe" role="group" aria-label="'+t('verlaufSpanne')+'">'+knoepfe+'</div>'+verlaufSvg(p)
  +'<p class="chart-note">'+t('verlaufNote').replace('{n}',p.length).replace('{min}',min).replace('{max}',max).replace('{seit}',new Date(alle[0].d+'T12:00:00').toLocaleDateString(document.documentElement.lang==='en'?'en-GB':'de-DE'))+'</p>';
}
async function zeigeVerlauf(){
 if(!panel||panel.hidden||!(IT.session||IT.member))return;
 let box=panel.querySelector('.verlauf');
 if(!box){box=document.createElement('section');box.className='verlauf';const intro=panel.querySelector('.detail-intro');if(!intro)return;intro.after(box)}
 box.innerHTML='<h3>'+t('verlaufTitel')+'</h3>'+verlaufHtml();
 if(!verlauf){await ladeVerlauf();const b=panel.querySelector('.verlauf');if(b)b.innerHTML='<h3>'+t('verlaufTitel')+'</h3>'+verlaufHtml()}
}
if(panel){
 new MutationObserver(()=>{if(!panel.querySelector('.verlauf'))zeigeVerlauf()}).observe(panel,{childList:true,attributes:true,attributeFilter:['hidden']});
 panel.addEventListener('click',e=>{const b=e.target.closest('[data-spanne],#verlauf-premium');if(!b)return;
  if(b.id==='verlauf-premium'){IT.oeffneKonto&&IT.oeffneKonto(b,'paywall');return}
  verlaufSpanne=Number(b.dataset.spanne);const box=panel.querySelector('.verlauf');box.innerHTML='<h3>'+t('verlaufTitel')+'</h3>'+verlaufHtml();box.querySelector('[data-spanne="'+verlaufSpanne+'"]')?.focus()});
}
document.addEventListener('investtimer:update',()=>{verlauf=null;const b=panel&&panel.querySelector('.verlauf');if(b)b.remove();zeigeVerlauf()});
