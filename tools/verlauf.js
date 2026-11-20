/* Verlauf des Marktstress im Detailbereich (angemeldet bzw. Premium). Eine durchgehende Linie.
   Verdichtung je Zeitraum: 1M/3M Tageswerte, 1J/5J Wochenwerte, Alle Monatswerte; bei Wochen- und Monatswerten
   zeigt eine dezente Flaeche die Spanne von Tief bis Hoch der Periode, damit Spitzen nicht verschwinden.
   Stressphasen (historie/ereignisse.json) als Baender (Mindestbreite), bei "Alle" nur Phasen mit Hoechstwert ab 70.
   Desktop: Kurzname im Band, Hover/Klick zeigt die Ereigniskarte. Mobil (< 760 px): wischbare Chip-Leiste. */
let verlauf=null,verlaufZeit=0,verlaufSpanne='1J',verlaufIndex=null,verlaufEreignis=null;
const vMobil=()=>window.matchMedia('(max-width:759px)').matches;
/* Eigene Ansicht #verlauf; Daten erst beim Oeffnen. Ausgeloggt nur bis zum zeitversetzten Datum (oeffentlicher Endpunkt). */
const vAn=()=>!!(IT.member&&(IT.session||(IT.emailVonSitzung&&IT.emailVonSitzung())));
const panel=document.createElement('section');panel.id='verlauf-ansicht';panel.className='verlauf-ansicht';panel.hidden=true;panel.setAttribute('aria-labelledby','verlauf-ansicht-titel');
($('.app-header')||document.body).after(panel);
let verlaufFuer=null;
const SPANNEN=[['1M',29,'taeglich'],['3M',92,'taeglich'],['1J',366,'woechentlich'],['5J',1827,'woechentlich'],['A',0,'monatlich']];
const V_BAND_MIN=70,V_BAND_BREITE=6;
async function ladeVerlauf(){
 const an=vAn();if(verlauf&&!verlauf.fehler&&verlaufFuer===an&&Date.now()-verlaufZeit<600000)return verlauf;
 try{verlauf=an?await api('historie'):await fetch('/api/historie-oeffentlich',{cache:'no-cache'}).then(r=>r.ok?r.json():Promise.reject(r.status))}catch(x){verlauf={fehler:x}}
 verlaufFuer=an;verlaufZeit=Date.now();return verlauf;
}
IT.ladeVerlauf=ladeVerlauf;
IT.verlaufZeitraum=()=>verlaufSpanne;
/* Ankunft ueber einen geteilten Link (/s/verlauf, /s/phase): Zeitraum bzw. Phase einmalig setzen */
function vStartAnwenden(){
 const s=IT.teilenStart;if(!s||!verlauf||verlauf.fehler)return;IT.teilenStart=null;
 if(s.z&&SPANNEN.some(x=>x[0]===s.z))verlaufSpanne=s.z;
 const e=s.phase&&(verlauf.ereignisse||[]).find(x=>x.id===s.phase);if(!e)return;verlaufEreignis=e.id;
 if(!s.z){const t=verlauf.taeglich||[],ende=t.length?vMs(t[t.length-1][0]):Date.now();verlaufSpanne=vMs(e.start)>=ende-1827*864e5||e.spitze.w<70?'5J':'A'}
}
const vLang=()=>document.documentElement.lang==='en'?'en-US':'de-DE';
const vMs=d=>Date.parse(d+'T12:00:00Z');
const vEn=()=>document.documentElement.lang==='en';
/* Monatswerte aus Wochenwerten, falls die API (aelterer Stand) keine liefert */
function vMonate(w){const m={};(w||[]).forEach(p=>{const k=p[0].slice(0,7),lo=p[4]??p[1],hi=p[5]??p[1],a=m[k];m[k]=a?[p[0],p[1],p[2],p[3],Math.min(a[4],lo),Math.max(a[5],hi)]:[p[0],p[1],p[2],p[3],lo,hi]});return Object.keys(m).sort().map(k=>m[k])}
/* Eine Quelle fuer den aktuellen Wert (Auftrag 20.11.2026): eingeloggt endet jede Reihe (Tag, laufende Woche, laufender Monat)
   mit dem Wert aus /api/aktuell (IT.live) - gleich wie Startseite, KI-Bruecke, KI-Eyebrow und Teilen. */
function vMitAktuell(reihe,art){
 const v=vAn()&&IT.live;if(!v||v.rounded==null||!v.asOf||!reihe.length)return reihe;
 const w=v.rounded,d=v.asOf,letzt=reihe[reihe.length-1];if(letzt[0]>d)return reihe;
 const kw=x=>{const t=new Date(vMs(x));t.setUTCDate(t.getUTCDate()-((t.getUTCDay()+6)%7));return t.toISOString().slice(0,10)};
 const gleich=art==='taeglich'?letzt[0]===d:art==='woechentlich'?kw(letzt[0])===kw(d):letzt[0].slice(0,7)===d.slice(0,7);
 const r=reihe.slice();
 if(gleich)r[r.length-1]=[d,w,letzt[2],'a'].concat(letzt.length>5?[Math.min(letzt[4],w),Math.max(letzt[5],w)]:[]);
 else r.push([d,w,v.count??14,'a'].concat(art==='taeglich'?[]:[w,w]));
 return r;
}
function vAuswahl(){
 const [,tage,art]=SPANNEN.find(s=>s[0]===verlaufSpanne)||SPANNEN[2];
 const reihe=vMitAktuell((art==='monatlich'&&!verlauf.monatlich?vMonate(verlauf.woechentlich):verlauf[art])||[],art);
 const ende=reihe.length?vMs(reihe[reihe.length-1][0]):Date.now(),start=tage?ende-tage*864e5:-Infinity;
 const p=reihe.filter(x=>vMs(x[0])>=start);
 const a=p.length?p[0][0]:'',b=p.length?p[p.length-1][0]:'';
 const e=(verlauf.ereignisse||[]).filter(x=>x.ende>a&&x.start<=b&&x.spitze&&x.spitze.d>=a&&x.spitze.d<=b&&(verlaufSpanne!=='A'||x.spitze.w>=V_BAND_MIN));
 return {p,e,art};
}
function vDatum(d){return new Date(vMs(d)).toLocaleDateString(vLang(),{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'})}
/* Zeichenflaeche in echter Breite (keine Skalierung der Schrift), Desktop etwas hoeher */
let vW=600,vH=180;const vL=30,vR=34,vT=10,vB=24;
const vBreite=()=>{const b=panel&&panel.querySelector('.verlauf');vW=Math.round(Math.min(1200,Math.max(280,b&&b.clientWidth||600)));vH=vW<560?180:230};
function vX(p){const a=vMs(p[0][0]),b=vMs(p[p.length-1][0]);return d=>vL+(b===a?(vW-vL-vR)/2:(vMs(d)-a)/(b-a)*(vW-vL-vR))}
const vY=w=>vT+(100-w)*(vH-vT-vB)/100;
/* Achsenmarken: Alle alle 5 Jahre, 5J jedes Jahr, 1J Quartale (Januar mit Jahr), 3M Monatsanfaenge, 1M Montage */
function vMarken(p){
 const a=vMs(p[0][0]),b=vMs(p[p.length-1][0]),o=[],da=new Date(a),f=(d,opt)=>d.toLocaleDateString(vLang(),Object.assign({timeZone:'UTC'},opt));
 if(verlaufSpanne==='A'||verlaufSpanne==='5J'){const s=verlaufSpanne==='A'?5:1;for(let j=Math.ceil(da.getUTCFullYear()/s)*s;;j+=s){const m=Date.UTC(j,0,1,12);if(m>b)break;if(m>=a)o.push([m,String(j)])}}
 else if(verlaufSpanne==='1J'||verlaufSpanne==='3M'){const s=verlaufSpanne==='1J'?3:1;for(let j=da.getUTCFullYear(),m=da.getUTCMonth()+1;;m++){if(m>11){m=0;j++}const z=Date.UTC(j,m,1,12);if(z>b)break;if(z<a||m%s)continue;const d=new Date(z);o.push([z,m===0?f(d,{month:'short',year:'numeric'}):f(d,{month:'short'})])}}
 else{for(let z=a;z<=b;z+=864e5){const d=new Date(z);if(d.getUTCDay()===1)o.push([z,f(d,{day:'numeric',month:'short'})])}}
 return o;
}
function stressSvg(p,x,e,art){
 const y=vY,lang=art!=='taeglich';
 let s='<svg class="chart-svg verlauf-svg" data-panel="stress" viewBox="0 0 '+vW+' '+vH+'" aria-hidden="true">';
 for(const g of [0,25,50,75,100])s+='<line class="chart-grid" x1="'+vL+'" x2="'+(vW-vR)+'" y1="'+y(g)+'" y2="'+y(g)+'"/><text class="chart-text" x="0" y="'+(y(g)+4)+'">'+g+'</text>';
 /* Achsenmarken ohne Ueberlappung */
 const a0=vMs(p[0][0]),a1=vMs(p[p.length-1][0]),xs=d=>vL+(a1===a0?0:(d-a0)/(a1-a0)*(vW-vL-vR));let frei=-1e9;
 vMarken(p).forEach(([d,txt])=>{const xx=xs(d),br=txt.length*6.2;if(xx-br/2<frei+8||xx+br/2>vW)return;frei=xx+br/2;
  s+='<line class="verlauf-marke" x1="'+xx.toFixed(1)+'" x2="'+xx.toFixed(1)+'" y1="'+(vH-vB)+'" y2="'+(vH-vB+4)+'"/><text class="chart-text" text-anchor="middle" x="'+xx.toFixed(1)+'" y="'+(vH-5)+'">'+esc(txt)+'</text>'});
 /* Stressphasen als Baender (Mindestbreite). Kurzname nur auf dem Desktop: hoechste Phasen zuerst, bis zwei Zeilen,
    nie ueberlappend und nie ueber den Rand der Zeichenflaeche; passt er nicht, bleibt nur das Band (Name in Karte/Tooltip).
    Am rechten Rand rechtsbuendig an der Bandkante. */
 const aktiv=vAktivId(e),reihen=[[],[]],texte=[],rechts=vW-vR-2;
 (e||[]).forEach(m=>{const [x0,bx]=vBand(m,x);
  s+='<rect class="verlauf-band'+(m.id===aktiv?' aktiv':'')+'" data-band="'+m.id+'" x="'+x0.toFixed(1)+'" y="'+vT+'" width="'+bx.toFixed(1)+'" height="'+(vH-vT-vB)+'" rx="1.5"/>'});
 if(!vMobil())(e||[]).slice().sort((u,v)=>v.spitze.w-u.spitze.w).forEach(m=>{const [x0,bx]=vBand(m,x),name=vEn()?m.kurz_en:m.kurz,br=vTextBreite(name);
  let a=x0+3,anker='start';if(a+br>rechts){a=x0+bx-3-br;anker='end'}
  if(a<vL+2||a+br>rechts)return;
  const r=reihen.findIndex(z=>z.every(([u,v])=>a+br<u-6||a>v+6));if(r<0)return;
  reihen[r].push([a,a+br]);texte.push('<text class="verlauf-band-text" data-label="'+m.id+'" text-anchor="'+anker+'" x="'+(anker==='end'?a+br:a).toFixed(1)+'" y="'+(vT+10+r*12)+'">'+esc(name)+'</text>')});
 s+=texte.join('');
 /* Spanne Tief bis Hoch je Periode */
 /* Spanne Tief bis Hoch entfernt (Nachtrag 2): nur die Linie */
 s+='<polyline class="chart-line verlauf-linie'+(lang?' verlauf-lang':'')+'" points="'+p.map(q=>x(q[0]).toFixed(1)+','+y(q[1]).toFixed(1)).join(' ')+'"/>';
 /* Endwert: Punkt exakt auf dem letzten Wert, Zahl rechts daneben (eigener Rand, keine Ueberlappung mit der Linie) */
 const z=p[p.length-1],zx=x(z[0]),zy=y(z[1]);
 s+='<circle class="verlauf-endpunkt" style="fill:'+ITStufe.farbe(z[1])+'" r="3.5" cx="'+zx.toFixed(1)+'" cy="'+zy.toFixed(1)+'"/><text class="chart-label verlauf-endwert" x="'+(zx+7).toFixed(1)+'" y="'+(Math.min(vH-vB-2,Math.max(vT+9,zy+4))).toFixed(1)+'">'+z[1]+'</text>';
 s+='<line class="verlauf-cursor" y1="'+vT+'" y2="'+(vH-vB)+'" x1="0" x2="0" visibility="hidden"/><circle class="verlauf-cursor-punkt" r="4" cx="0" cy="0" visibility="hidden"/></svg>';
 return s;
}
let vMessung=null;
function vTextBreite(txt){try{if(!vMessung){vMessung=document.createElement('canvas').getContext('2d');const f=getComputedStyle(document.body).getPropertyValue('--sans')||'sans-serif';vMessung.font='10px '+f}return Math.ceil(vMessung.measureText(txt).width*1.08)+1}catch{return txt.length*6}}
/* Band mit Mindestbreite, mittig ueber dem echten Zeitraum, innerhalb der Zeichenflaeche */
function vBand(m,x){let x0=Math.max(vL,x(m.start)),x1=Math.min(vW-vR,x(m.ende));if(x1-x0<V_BAND_BREITE){const c=(x0+x1)/2;x0=Math.max(vL,Math.min(vW-vR-V_BAND_BREITE,c-V_BAND_BREITE/2));x1=x0+V_BAND_BREITE}return [x0,x1-x0]}
function verlaufHtml(){
 const v=verlauf;vBreite();
 if(!v)return '<p class="chart-note">'+t('alarmLaedt')+'</p>';
 if(v.fehler==='premium')return '<p class="chart-note">'+t('verlaufPremium')+'</p><button type="button" class="primary" id="verlauf-premium">'+t('premiumAnsehen')+'</button>';
 if(v.fehler||!(v.taeglich||[]).length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const {p,e,art}=vAuswahl();if(!p.length)return '<p class="chart-note">'+t('verlaufFehlt')+'</p>';
 const x=vX(p),aktiv=vAktivId(e);
 const knoepfe=SPANNEN.map(([k])=>'<button type="button" class="verlauf-spanne'+(k===verlaufSpanne?' aktiv':'')+'" data-spanne="'+k+'" aria-pressed="'+(k===verlaufSpanne)+'">'+(k==='A'?t('verlaufAlle'):k==='1J'?t('verlauf1J'):k==='5J'?t('verlauf5J'):k)+'</button>').join('');
 const name=m=>vEn()?m.name_en:m.name;
 /* Desktop: unsichtbare Schaltflaechen ueber den Baendern (Tab, Enter, Hover); mobil: Chips */
 const baender=vMobil()?'':'<div class="verlauf-baender">'+e.map(m=>{const [x0,bx]=vBand(m,x);
  return '<button type="button" class="verlauf-band-knopf" data-ereignis="'+m.id+'" aria-pressed="'+(m.id===aktiv)+'" aria-label="'+esc(name(m)+', '+vZeitraum(m))+'" style="left:'+(x0/vW*100).toFixed(2)+'%;width:'+(bx/vW*100).toFixed(2)+'%;top:'+(vT/vH*100).toFixed(2)+'%;height:'+((vH-vT-vB)/vH*100).toFixed(2)+'%"></button>'}).join('')+'</div>';
 const chips=e.length?'<div class="verlauf-chips" role="group" aria-label="'+t('ereignisseLabel')+'">'+e.slice().reverse().map(m=>'<button type="button" class="verlauf-chip" data-ereignis="'+m.id+'" aria-pressed="'+(m.id===aktiv)+'">'+esc(vEn()?m.kurz_en:m.kurz)+'</button>').join('')+'</div>':'';
const legende='';/* ohne Legende */ const _legendeAlt=art==='taeglich'?'':'<p class="verlauf-legende"><span><i class="legende-linie" aria-hidden="true"></i>'+t(art==='monatlich'?'schlussMonat':'schlussWoche')+'</span><span><i class="legende-flaeche" aria-hidden="true"></i>'+t(art==='monatlich'?'flaecheMonat':'flaecheWoche')+'</span></p>';
 return '<div class="verlauf-kopf"><div class="verlauf-knoepfe" role="group" aria-label="'+t('verlaufSpanne')+'">'+knoepfe+'</div>'+(IT.teilenKnopf?IT.teilenKnopf('verlauf'):'')+'</div>'
  +'<div class="verlauf-wertzeile" role="status" aria-live="polite" aria-atomic="true">'+vWertzeileHtml(null)+'</div>'
  +'<div class="verlauf-diagramm" tabindex="0" role="group" aria-label="'+esc(t('verlaufAria').replace('{n}',p.length))+'">'
  +stressSvg(p,x,e,art)+baender+'</div>'
  +legende+chips+'<div class="ereignis-karte" aria-live="polite"'+(aktiv?'':' hidden')+'>'+vKarte(e.find(m=>m.id===aktiv))+'</div>'
  ;
}
/* Aktives Ereignis: gewaehltes, wenn sichtbar; sonst das juengste im sichtbaren Zeitraum */
function vAktivId(e){if(!e||!e.length)return null;if(verlaufEreignis&&e.some(m=>m.id===verlaufEreignis))return verlaufEreignis;return e[e.length-1].id}
function vMonat(d){return new Date(vMs(d)).toLocaleDateString(vLang(),{month:'short',year:'numeric',timeZone:'UTC'})}
function vZeitraum(m){const ende=new Date(vMs(m.ende)-864e5).toISOString().slice(0,10),a=vMonat(m.start),b=vMonat(ende);return a===b?a:a+' – '+b}
function vKarte(m){
 if(!m)return '';
 const nm=vEn()?m.name_en:m.name,bl=m.bloecke||{};
 const zeile=(k,l)=>bl[k]==null?'':'<div class="trieb-zeile"><span class="trieb-name">'+esc(t(l))+'</span><b>'+Math.round(bl[k])+'</b><span class="trieb-balken" aria-hidden="true"><i style="width:'+Math.round(bl[k])+'%;background:'+ITStufe.farbe(bl[k])+'"></i></span></div>';
 return '<div class="karte-kopf"><h4>'+esc(nm)+'</h4>'+(IT.teilenKnopf?IT.teilenKnopf('phase',m.id):'')+'</div><p class="karte-zeit">'+esc(vZeitraum(m))+'</p>'
  +'<dl class="karte-zahlen"><div><dt>'+t('karteHoechst')+'</dt><dd>'+t('karteAm').replace('{w}',m.spitze.w).replace('{d}',vDatum(m.spitze.d))+'</dd></div>'
  +'<div><dt>'+t('karteUnter40')+'</dt><dd>'+(m.unter40?t('karteNachTagen').replace('{n}',m.unter40.tage):t('karteNochNicht'))+'</dd></div></dl>'
  +(m.bloecke?'<p class="karte-trieb-titel">'+t('karteTrieb').replace('{d}',vDatum(m.spitze.d))+'</p>'+zeile('volatility','triebVol')+zeile('price','triebPreis')+zeile('positioning','triebStimmung'):'')
  +(IT.kiBruecke?IT.kiBruecke.phaseHtml(m):'');
}
/* Chip-Leiste: Verlauf am Rand als Scroll-Hinweis, aktiven Chip in Sicht holen (nur die Leiste scrollt, nie die Seite) */
function vChipsRand(c){if(!c)return;const max=c.scrollWidth-c.clientWidth;c.classList.toggle('rand-l',c.scrollLeft>2);c.classList.toggle('rand-r',max-c.scrollLeft>2)}
function vChipInSicht(box,weich){
 const c=box&&box.querySelector('.verlauf-chips'),a=c&&c.querySelector('[aria-pressed=true]');if(!c)return;
 if(a){const ziel=a.offsetLeft-c.offsetLeft-(c.clientWidth-a.offsetWidth)/2,z=Math.max(0,Math.min(c.scrollWidth-c.clientWidth,ziel));
  if(c.scrollTo)c.scrollTo({left:z,behavior:weich&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'auto'});else c.scrollLeft=z}
 vChipsRand(c);if(!c.dataset.rand){c.dataset.rand='1';c.addEventListener('scroll',()=>vChipsRand(c),{passive:true})}
}
function vAktiviere(id){
 verlaufEreignis=id;const box=panel.querySelector('.verlauf');if(!box)return;const {e}=vAuswahl(),m=e.find(x=>x.id===id);if(!m)return;
 box.querySelectorAll('[data-band]').forEach(r=>r.classList.toggle('aktiv',r.dataset.band===id));
 box.querySelectorAll('[data-ereignis]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.ereignis===id)));
 const k=box.querySelector('.ereignis-karte');if(k){k.innerHTML=vKarte(m);k.hidden=false;IT.kiBruecke&&IT.kiBruecke.beleben(k)}
 IT.teilenVorladen&&IT.teilenVorladen('phase',id);
 vChipInSicht(box,true);
}
/* Teilen-Bilder des sichtbaren Zeitraums und der offenen Ereigniskarte im Hintergrund vorhalten */
function vVorladen(){if(!IT.teilenVorladen||panel.hidden||!verlauf||verlauf.fehler)return;IT.teilenVorladen('verlauf');
 const a=panel.querySelector('.ereignis-karte .teilen-knopf');if(a)IT.teilenVorladen('phase',a.dataset.phase)}
function vZeichnen(fokus){
 const box=panel&&panel.querySelector('.verlauf');if(!box)return;
 vPos=null;verlaufIndex=null;box.innerHTML=verlaufHtml();vChipInSicht(box,false);vKopf();IT.kiBruecke&&IT.kiBruecke.beleben(box);vVorladen();
 if(fokus)box.querySelector(fokus)?.focus();
}
/* Erkunden per Finger, Stift und Maus (Pointer-Events), Tastatur: Werte-Zeile fest ueber dem Chart (nie unter dem Finger, nie am Rand),
   senkrechte Linie und Punkt in Stufenfarbe. Positionen sind beim Zeichnen vorberechnet (vPos), der naechste Punkt wird per binaerer
   Suche gefunden, gezeichnet wird hoechstens einmal pro Frame. Senkrecht wischen scrollt weiter die Seite (touch-action: pan-y). */
let vPos=null,vRaf=0,vZiel=null,vAus=null,vGeste=null;
function vPositionen(){const {p,e,art}=vAuswahl();if(!p.length){vPos=null;return}const x=vX(p);vPos={p,e,art,xs:p.map(q=>x(q[0]))}}
function vNaechster(xv){const xs=vPos.xs;let lo=0,hi=xs.length-1;while(lo<hi){const m=(lo+hi)>>1;if(xs[m]<xv)lo=m+1;else hi=m}
 return lo>0&&xv-xs[lo-1]<xs[lo]-xv?lo-1:lo}
function vZeitpunkt(q,art){const tag=new Date(vMs(q[0])).toLocaleDateString(vLang(),{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
 return art==='monatlich'?new Date(vMs(q[0])).toLocaleDateString(vLang(),{month:'long',year:'numeric',timeZone:'UTC'}):art==='woechentlich'?t('tipWoche').replace('{d}',tag):tag}
function vWertzeileHtml(i){
 if(!vPos)vPositionen();if(!vPos)return '';
 const {p,e,art}=vPos,ende=i==null,q=p[ende?p.length-1:i];
 const wann=ende?(vAn()?(vEn()?'Today':'Heute'):vZeitpunkt(q,'taeglich')):vZeitpunkt(q,art);
 const ph=ende?null:(e||[]).find(m=>q[0]>=m.start&&q[0]<m.ende);
 return '<span class="wz-punkt" style="background:'+ITStufe.farbe(q[1])+'" aria-hidden="true"></span><span class="wz-text">'+esc(wann)+' · '+esc(t('tipWert').replace('{w}',q[1]))+'</span>'
  +(ph?'<button type="button" class="wz-phase" data-ereignis="'+ph.id+'">'+esc(vEn()?ph.kurz_en:ph.kurz)+'</button>':'');
}
function vZeige(i){
 if(!vPos)vPositionen();if(!vPos)return;
 i=Math.max(0,Math.min(vPos.p.length-1,i));if(i===verlaufIndex&&!vAus)return;verlaufIndex=i;vZiel=i;
 if(!vRaf)vRaf=requestAnimationFrame(vMalen);
}
function vMalen(){
 vRaf=0;const dia=panel.querySelector('.verlauf-diagramm'),z=panel.querySelector('.verlauf-wertzeile');if(!dia||!vPos)return;
 const i=vZiel;if(i==null)return;const q=vPos.p[i],x=vPos.xs[i],y=vY(q[1]),f=ITStufe.farbe(q[1]);
 const l=dia.querySelector('.verlauf-cursor'),c=dia.querySelector('.verlauf-cursor-punkt');
 l.setAttribute('x1',x);l.setAttribute('x2',x);l.style.stroke=f;c.setAttribute('cx',x);c.setAttribute('cy',y);c.style.fill=f;
 dia.classList.add('erkunden');dia.classList.remove('ausblenden');z.classList.add('erkunden');z.innerHTML=vWertzeileHtml(i);
}
function vVerberge(sofort){
 clearTimeout(vAus);vAus=null;verlaufIndex=null;vZiel=null;
 const dia=panel.querySelector('.verlauf-diagramm'),z=panel.querySelector('.verlauf-wertzeile');if(!dia)return;
 const fertig=()=>{dia.classList.remove('erkunden','ausblenden');if(z){z.classList.remove('erkunden');z.innerHTML=vWertzeileHtml(null)}};
 if(sofort){fertig();return}
 dia.classList.add('ausblenden');vAus=setTimeout(fertig,260);
}
function vSpaeterVerbergen(){clearTimeout(vAus);vAus=setTimeout(()=>vVerberge(false),2000)}
function vIndexBei(ev){
 const dia=panel.querySelector('.verlauf-diagramm'),svg=dia&&dia.querySelector('[data-panel=stress]');if(!svg)return null;
 if(!vPos)vPositionen();if(!vPos)return null;
 const r=svg.getBoundingClientRect();return vNaechster((ev.clientX-r.left)/r.width*vW);
}
function vKopf(){
 const k=panel.querySelector('.verlauf-ansicht-kopf');if(!k)return;
 const gesperrt=!vAn()&&verlauf&&!verlauf.fehler;
 k.innerHTML='<div><span class="eyebrow verlauf-eyebrow">'+esc(t('verlaufEyebrow'))+'</span><h2 id="verlauf-ansicht-titel" tabindex="-1">'+esc(t('verlaufTitel'))+'<button type="button" class="verlauf-info" aria-expanded="false" aria-controls="verlauf-info-text" aria-label="'+esc(t('verlaufInfoLabel'))+'">i</button></h2><p class="verlauf-info-text" id="verlauf-info-text" role="note" hidden>'+esc(t('verlaufInfo'))+'</p></div>'
  +(gesperrt?'<p class="verlauf-gesperrt"><span>'+esc(t('verlaufNeuer'))+'</span> <button type="button" class="text-button" data-ki-login>'+esc(t('loginSubmit'))+'</button></p>':'');
}
function zeigeVerlauf(){
 const fokus=document.activeElement&&document.activeElement.id==='verlauf-ansicht-titel';
 panel.innerHTML='<header class="verlauf-ansicht-kopf"></header><div class="verlauf"></div>';
 const box=panel.querySelector('.verlauf');vKopf();
 const frisch=verlauf&&!verlauf.fehler&&verlaufFuer===vAn();
 if(frisch)vStartAnwenden();
 vPos=null;box.innerHTML=verlaufHtml();
 if(fokus)$('#verlauf-ansicht-titel')?.focus({preventScroll:true});
 if(!frisch){if(verlauf&&verlaufFuer!==vAn())verlauf=null;vPos=null;box.innerHTML=verlaufHtml();ladeVerlauf().then(()=>{vStartAnwenden();if(!panel.hidden)vZeichnen()})}else{vChipInSicht(box,false);vVorladen()}
}
IT.verlaufAnsicht={zeigen(){const war=panel.hidden;panel.hidden=false;if(war||!panel.querySelector('.verlauf'))zeigeVerlauf()},verbergen(){panel.hidden=true}};
if(panel){
 panel.addEventListener('click',e=>{const wz=e.target.closest('.verlauf-wertzeile'),ph=wz&&wz.querySelector('.wz-phase');
  const ev=e.target.closest('[data-ereignis]')||ph;if(ev){vAktiviere(ev.dataset.ereignis);if(ph)panel.querySelector('.ereignis-karte')?.scrollIntoView({block:'nearest',behavior:'smooth'});return}
  const b=e.target.closest('[data-spanne],#verlauf-premium');if(!b)return;
  if(b.id==='verlauf-premium'){IT.oeffneKonto&&IT.oeffneKonto(b,'paywall');return}
  verlaufSpanne=b.dataset.spanne;vZeichnen('[data-spanne="'+verlaufSpanne+'"]')});
 panel.addEventListener('pointerover',e=>{const b=e.target.closest('.verlauf-band-knopf');if(b&&e.pointerType==='mouse')vAktiviere(b.dataset.ereignis)});
 /* Finger/Stift: Auflegen zeigt sofort den naechsten Punkt; waagerecht folgen; senkrechtes Wischen ueberlaesst die Geste dem Browser
    (pointercancel -> sofort weg); Loslassen: 2 s stehen, dann sanft ausblenden. Maus: Hover folgt, Verlassen blendet aus. */
 panel.addEventListener('pointerdown',e=>{
  if(!e.target.closest('.verlauf-diagramm'))return;
  if(e.target.closest('.verlauf-band-knopf')&&e.pointerType==='mouse')return;
  clearTimeout(vAus);vAus=null;vGeste={id:e.pointerId,x:e.clientX,y:e.clientY,t:e.timeStamp,typ:e.pointerType};
  const i=vIndexBei(e);if(i!=null)vZeige(i)});
 panel.addEventListener('pointermove',e=>{
  if(e.pointerType==='mouse'){if(e.target.closest('.verlauf-diagramm')){clearTimeout(vAus);vAus=null;const i=vIndexBei(e);if(i!=null)vZeige(i)}return}
  if(!vGeste||e.pointerId!==vGeste.id)return;const i=vIndexBei(e);if(i!=null)vZeige(i)});
 const ende=e=>{if(vGeste&&e.pointerId===vGeste.id){vGeste=null;if(e.type==='pointercancel')vVerberge(true);else vSpaeterVerbergen()}};
 panel.addEventListener('pointerup',ende);panel.addEventListener('pointercancel',ende);
 panel.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse'&&e.target.classList&&e.target.classList.contains('verlauf-diagramm'))vVerberge(false)},true);
 /* Tippen bzw. Klicken irgendwo ausserhalb von Chart und Werte-Zeile schliesst sofort */
 document.addEventListener('pointerdown',e=>{if(verlaufIndex!=null&&!e.target.closest('.verlauf-diagramm,.verlauf-wertzeile'))vVerberge(true)},true);
 /* iOS: kein Kontextmenue (Kopieren/Nachschlagen) beim Gedrueckthalten im Chart */
 panel.addEventListener('contextmenu',e=>{if(e.target.closest('.verlauf-diagramm,.verlauf-wertzeile'))e.preventDefault()});
 panel.addEventListener('keydown',e=>{if(!e.target.classList||!e.target.classList.contains('verlauf-diagramm'))return;
  const n=vAuswahl().p.length;let i=verlaufIndex==null?n-1:verlaufIndex;
  if(e.key==='ArrowLeft')i--;else if(e.key==='ArrowRight')i++;else if(e.key==='Home')i=0;else if(e.key==='End')i=n-1;else if(e.key==='Escape'){vVerberge(true);return}else return;
  e.preventDefault();vZeige(i)});
 panel.addEventListener('focusin',e=>{if(e.target.classList&&e.target.classList.contains('verlauf-diagramm'))vZeige(verlaufIndex==null?vAuswahl().p.length-1:verlaufIndex)});
 /* Fokus weg (z. B. Tippen auf die Phase in der Werte-Zeile): wie Loslassen erst nach 2 s ausblenden, sonst waere der Phasen-Knopf vor dem Klick weg */
 panel.addEventListener('focusout',e=>{if(e.target.classList&&e.target.classList.contains('verlauf-diagramm'))vSpaeterVerbergen()});
}
let vGroesse=null;window.addEventListener('resize',()=>{clearTimeout(vGroesse);vGroesse=setTimeout(()=>{if(verlauf&&panel&&panel.querySelector('.verlauf-diagramm')){const alt=vW,altM=panel.querySelector('.verlauf-chips')!=null;vBreite();if(alt!==vW||altM!==vMobil())vZeichnen();else vChipsRand(panel.querySelector('.verlauf-chips'))}},150)});
document.addEventListener('investtimer:update',()=>{if(verlaufFuer!==vAn()){verlauf=null}if(!panel.hidden)zeigeVerlauf()});
new MutationObserver(()=>{if(!panel.hidden&&verlauf&&panel.querySelector('.verlauf'))vZeichnen()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
/* Startseite (nur ausgeloggt): kleiner 1J-Ausschnitt ohne Bedienelemente, Daten erst wenn er ins Bild kommt */
const vMini=document.createElement('section');vMini.className='verlauf-mini';vMini.hidden=true;vMini.setAttribute('aria-labelledby','verlauf-mini-titel');
($('#details-toggle')||{before:()=>{}}).before(vMini);
let vMiniDaten=null,vMiniLaedt=false;
function vMiniHtml(){
 const d=vMiniDaten;if(!d||d.fehler)return '';
 const reihe=d.woechentlich||[];if(reihe.length<2)return '';
 const ende=vMs(reihe[reihe.length-1][0]),p=reihe.filter(q=>vMs(q[0])>=ende-366*864e5);if(p.length<2)return '';
 const W=600,H=110,a=vMs(p[0][0]),x=q=>(vMs(q[0])-a)/(ende-a||1)*W,y=w=>6+(100-w)*(H-12)/100,z=p[p.length-1];
 const fmt=(q,o)=>new Date(vMs(q[0])).toLocaleDateString(vLang(),Object.assign({timeZone:'UTC'},o));
 return '<div class="verlauf-mini-kopf"><h2 id="verlauf-mini-titel">'+esc(t('verlaufMiniTitel'))+'</h2><a href="#verlauf" class="verlauf-mini-link">'+esc(t('verlaufMiniLink'))+'</a></div>'
  +'<div class="verlauf-mini-flaeche" role="img" aria-label="'+esc(t('verlaufMiniAria').replace('{a}',fmt(p[0],{month:'long',year:'numeric'})).replace('{b}',fmt(z,{day:'numeric',month:'long',year:'numeric'})).replace('{w}',z[1]))+'">'
  +'<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" aria-hidden="true"><line class="verlauf-mini-mitte" x1="0" x2="'+W+'" y1="'+y(50)+'" y2="'+y(50)+'"/>'
  +'<polyline points="'+p.map(q=>x(q).toFixed(1)+','+y(q[1]).toFixed(1)).join(' ')+'"/></svg>'
  +'<span class="verlauf-mini-punkt" style="background:'+ITStufe.farbe(z[1])+';left:100%;top:'+(y(z[1])/H*100).toFixed(2)+'%"></span></div>'
  +'<p class="verlauf-mini-achse"><span>'+esc(fmt(p[0],{month:'short',year:'numeric'}))+'</span><span>'+esc(t('verlaufMiniEnde').replace('{w}',z[1]).replace('{d}',fmt(z,{day:'numeric',month:'short'})))+'</span></p>';
}
/* Platz ist ausgeloggt schon beim Laden reserviert (kein Layoutsprung, wenn die Daten nach dem ersten Zeichnen kommen) */
function vMiniZeichnen(){vMini.style.minHeight='';vMini.hidden=vAn()||!vMiniDaten||!!vMiniDaten.fehler;if(!vMini.hidden)vMini.innerHTML=vMiniHtml();if(!vMini.innerHTML)vMini.hidden=true}
async function vMiniLaden(){
 if(vMiniLaedt||vAn())return;vMiniLaedt=true;
 try{vMiniDaten=await fetch('/api/historie-oeffentlich',{cache:'no-cache'}).then(r=>r.ok?r.json():Promise.reject(r.status))}catch(x){vMiniDaten={fehler:x}}
 vMiniZeichnen();
}
if('IntersectionObserver' in window){const io=new IntersectionObserver(e=>{if(e.some(x=>x.isIntersecting)){io.disconnect();vMiniLaden()}},{rootMargin:'300px'});
 /* leerer Platzhalter (Hoehe 0) nur zum Beobachten; sichtbar wird der Ausschnitt erst mit Daten */
 vMini.hidden=false;if(!vAn())vMini.style.minHeight='var(--mini-h,164px)';io.observe(vMini)}
else vMiniLaden();
document.addEventListener('investtimer:update',()=>{if(vAn())vMini.hidden=true;else if(vMiniDaten)vMiniZeichnen();else vMiniLaden()});
new MutationObserver(()=>{if(vMiniDaten&&!vAn())vMiniZeichnen()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});

/* Info-Symbol am Verlauf-Titel: Tippen/Klick schaltet um, Hover/Fokus zeigt (Desktop) */
document.addEventListener('click',e=>{const b=e.target.closest('.verlauf-info'),t2=document.getElementById('verlauf-info-text');
 if(!t2)return;if(b){const auf=t2.hidden;t2.hidden=!auf;b.setAttribute('aria-expanded',String(auf));return}
 if(!t2.hidden&&!e.target.closest('#verlauf-info-text')){t2.hidden=true;document.querySelector('.verlauf-info')?.setAttribute('aria-expanded','false')}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const t2=document.getElementById('verlauf-info-text');if(t2&&!t2.hidden){t2.hidden=true;document.querySelector('.verlauf-info')?.focus()}}});

/* Neu holen bei Rueckkehr in die App: Daten im Hintergrund laden, dann ohne Flackern neu zeichnen (Zeitraum bleibt) */
IT.verlaufNeu=async()=>{verlaufZeit=0;await ladeVerlauf();if(!panel.hidden&&panel.querySelector('.verlauf'))vZeichnen()};
