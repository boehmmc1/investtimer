/* KI-Bereich: eigene Ansicht (#ki) mit Navigation (Desktop: Tabs im Header, mobil: Leiste unten),
   Neuronen-Kugel (Fibonacci-Kugel wie im Volafly-Neural-Core, in InvestTimer-Gruen), Startansicht mit Fragegruppen,
   Gespraech mit Belegen (Verlaufsausschnitt, Teilwerte) und Folgefragen. Gespraech bleibt im App-Zustand (nicht gespeichert).
   "Frag die KI dazu" (Wert, Ereigniskarten) oeffnet die Ansicht mit vorausgefuellter Frage, ohne zu senden. */
(()=>{
const KI_FRAGEN=__KI_FRAGEN__;
const KT={de:{
 tabStress:'Marktstress',tabKi:'KI',tabVerlauf:'Verlauf',tabKonto:'Konto',nav:'Bereiche',
 eyebrow:'INVESTTIMER KI',eyebrowWert:'INVESTTIMER KI · STAND HEUTE {w}',titel:'Was bewegt dich am Markt?',
 unter:'Frag nach dem aktuellen Wert, seinen Treibern oder einer Phase aus dem Verlauf. Die KI antwortet mit den Daten von InvestTimer.',
 platzhalter:'Deine Frage an die KI',senden:'Frage senden',hinweis:'Antworten erzeugt eine KI und können Fehler enthalten · Keine Anlageberatung',
 rest:'Noch {n} Fragen heute',rest1:'Noch eine Frage heute',rest0:'Für heute keine Fragen mehr',
 anmelden:'Anmelden & KI fragen',ausgeloggt:'Die KI ist nach der Anmeldung verfügbar. Beispiele, was du fragen kannst:',
 kopf:'InvestTimer KI · Stand heute {w}',kopfOhne:'InvestTimer KI',neu:'Neues Gespräch',denkt:'InvestTimer liest die Daten …',
 du:'Deine Frage',ki:'Antwort der KI',weiter:'Passende Folgefragen',belegTitel:'Marktstress {a} bis {b}',belegTag:'{w} am {d}',
 teilwerte:'Teilwerte am {d}',vol:'Kursschwankungen',preis:'Breite und Trend',stimmung:'Stimmung und Absicherung',
 fLimit:'Für heute sind deine Fragen aufgebraucht. Morgen kannst du wieder fragen.',
 fLogin:'Deine Anmeldung ist abgelaufen. Melde dich neu an, dann kannst du weiterfragen.',fLoginKnopf:'Neu anmelden',
 fAus:'Die KI ist gerade ausgeschaltet. Versuch es später noch einmal.',
 fNetz:'Keine Verbindung zur KI. Prüf dein Netz und versuch es gleich noch einmal.',
 fragKi:'Frag die KI dazu',zeile:'Frag die KI zum Wert …',zeileLabel:'Frage an die KI',zumKi:'Zur KI',
 frageWert:'Warum steht der Marktstress bei {w}?',frageEreignis:'Was hat den Marktstress in der Phase {n} getrieben?',
 verlaufLogin:'Den Verlauf seit 2006 siehst du nach der Anmeldung.',verlaufLoginKnopf:'Anmelden'
},en:{
 tabStress:'Market stress',tabKi:'AI',tabVerlauf:'History',tabKonto:'Account',nav:'Sections',
 eyebrow:'INVESTTIMER AI',eyebrowWert:'INVESTTIMER AI · TODAY {w}',titel:'What’s on your mind about the market?',
 unter:'Ask about today’s reading, what drives it, or a phase from the history. The AI answers with InvestTimer data.',
 platzhalter:'Ask the AI',senden:'Send question',hinweis:'AI-generated answers may contain errors · Not investment advice',
 rest:'{n} questions left today',rest1:'1 question left today',rest0:'No questions left today',
 anmelden:'Sign in to ask the AI',ausgeloggt:'The AI is available after you sign in. Here’s what you can ask:',
 kopf:'InvestTimer AI · Today {w}',kopfOhne:'InvestTimer AI',neu:'New conversation',denkt:'InvestTimer is reading the data …',
 du:'Your question',ki:'AI answer',weiter:'Follow-up questions',belegTitel:'Market stress {a} to {b}',belegTag:'{w} on {d}',
 teilwerte:'Sub-scores on {d}',vol:'Volatility',preis:'Breadth and trend',stimmung:'Sentiment and hedging',
 fLimit:'You’ve used today’s questions. You can ask again tomorrow.',
 fLogin:'Your session has expired. Sign in again to keep asking.',fLoginKnopf:'Sign in again',
 fAus:'The AI is switched off right now. Try again later.',
 fNetz:'Can’t reach the AI. Check your connection and try again.',
 fragKi:'Ask the AI about this',zeile:'Ask the AI about this reading …',zeileLabel:'Question for the AI',zumKi:'Go to AI',
 frageWert:'Why is market stress at {w}?',frageEreignis:'What drove market stress during {n}?',
 verlaufLogin:'Sign in to see the history back to 2006.',verlaufLoginKnopf:'Sign in'
}};
const sp=()=>document.documentElement.lang==='en'?'en':'de';
const kt=k=>KT[sp()][k]||KT.de[k]||k;
const mobil=()=>matchMedia('(max-width:759px)').matches;
const angemeldet=()=>!!(IT.member&&(IT.session||(IT.emailVonSitzung&&IT.emailVonSitzung())));
const wert=()=>{const v=IT.member&&IT.live?IT.live:null;return v&&v.rounded!=null?v.rounded:null};
const datumLang=d=>new Date(Date.parse(d+'T12:00:00Z')).toLocaleDateString(sp()==='en'?'en-US':'de-DE',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
const datumKurz=d=>new Date(Date.parse(d+'T12:00:00Z')).toLocaleDateString(sp()==='en'?'en-US':'de-DE',{month:'short',year:'numeric',timeZone:'UTC'});
const SVG={stress:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17a8 8 0 0 1 16 0"/><path d="M12 17l4-5"/></svg>',
 ki:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.2"/><path d="M12 4v5.8M12 14.2V20M4.6 9l5.3 2M14.1 13l5.3 2M4.6 15l5.3-2M14.1 11l5.3-2"/></svg>',
 verlauf:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 18l5-6 4 3 5-8 4 4"/><path d="M3 21h18"/></svg>',
 konto:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="3.6"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
 pfeil:'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 16V4M5 9l5-5 5 5"/></svg>'};

/* ---------- Neuronen-Kugel ---------- */
function kugel(canvas,opt){
 const ctx=canvas.getContext('2d'),n=opt.punkte,grenze=opt.grenze;
 const knoten=Array.from({length:n},(_,i)=>{const y=1-i/(n-1)*2,r=Math.sqrt(1-y*y),a=i*2.39996;return {x:Math.cos(a)*r,y,z:Math.sin(a)*r}});
 const kanten=[];knoten.forEach((a,i)=>knoten.forEach((b,j)=>{if(j>i&&Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z)<grenze)kanten.push([i,j])}));
 const ruhig=matchMedia('(prefers-reduced-motion: reduce)').matches,TAU=Math.PI*2;
 let w=0,h=0,zeit=opt.start||0,vorher=0,raf=0,sichtbar=true,tempo=1;
 const G='46,109,92',H='120,170,140';
 function zeichne(){
  if(!w||!h)return;ctx.clearRect(0,0,w,h);
  const cx=w/2,cy=h/2,r=Math.min(w,h)*(opt.radius||.36);
  if(opt.schein){const g=ctx.createRadialGradient(cx,cy,0,cx,cy,Math.min(r*1.6,Math.min(w,h)/2));g.addColorStop(0,'rgba('+G+',.10)');g.addColorStop(.65,'rgba('+G+',.04)');g.addColorStop(1,'rgba('+G+',0)');ctx.fillStyle=g;ctx.fillRect(0,0,w,h)}
  const win=zeit*.11,neig=.2;
  const ps=knoten.map(p=>{const x=p.x*Math.cos(win)+p.z*Math.sin(win),z=-p.x*Math.sin(win)+p.z*Math.cos(win);const y=p.y*Math.cos(neig)-z*Math.sin(neig),zz=p.y*Math.sin(neig)+z*Math.cos(neig);const sc=1+zz*.12;return {x:cx+x*r*sc,y:cy+y*r*sc,z:zz}});
  kanten.forEach(([i,j],k)=>{const a=ps[i],b=ps[j],al=.08+((a.z+b.z+2)/4)*.3;
   ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle='rgba('+G+','+al.toFixed(3)+')';ctx.lineWidth=opt.linie||.7;ctx.stroke();
   if(opt.impulse&&k%29===0){const q=(zeit*.15+k*.079)%1;ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*q,a.y+(b.y-a.y)*q,1.3,0,TAU);ctx.fillStyle='rgba('+G+',.9)';ctx.fill()}});
  ps.slice().sort((a,b)=>a.z-b.z).forEach((p,i)=>{const al=(p.z+1)*.32+.2;ctx.beginPath();ctx.arc(p.x,p.y,(opt.punkt||.65)+(p.z+1)*(opt.punktZu||.55),0,TAU);ctx.fillStyle='rgba('+(p.z>.3?G:H)+','+al.toFixed(3)+')';ctx.fill()});
 }
 function groesse(){const b=canvas.getBoundingClientRect();if(!b.width||!b.height)return;w=b.width;h=b.height;const d=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);ctx.setTransform(d,0,0,d,0,0);zeichne()}
 function bild(ms){const dt=Math.min((ms-vorher)/1000,.05);vorher=ms;if(sichtbar&&!document.hidden&&!ruhig)zeit+=dt*tempo;zeichne();raf=sichtbar&&!document.hidden&&!ruhig?requestAnimationFrame(bild):0}
 function weiter(){if(!raf&&!ruhig&&sichtbar&&!document.hidden){vorher=performance.now();raf=requestAnimationFrame(bild)}}
 new ResizeObserver(groesse).observe(canvas);
 new IntersectionObserver(e=>{sichtbar=e[0].isIntersecting;if(sichtbar)weiter()}).observe(canvas);
 document.addEventListener('visibilitychange',weiter);
 groesse();weiter();
 return {tempo:v=>{tempo=v;weiter()},zeichne};
}

/* ---------- Zustand ---------- */
const st={gespraech:[],busy:false,rest:null,notiz:'',restGeladen:false};
let ansicht=null,grosseKugel=null,kleineKugel=null,haftUnten=true;

/* ---------- Navigation ---------- */
const kopf=$('.app-header'),werkzeuge=kopf&&kopf.querySelector('.header-tools');
const tabs=document.createElement('nav');tabs.className='it-tabs';
const leiste=document.createElement('nav');leiste.className='it-leiste';
function navRender(){
 const a=aktiv();
 tabs.setAttribute('aria-label',kt('nav'));leiste.setAttribute('aria-label',kt('nav'));
 tabs.innerHTML=[['stress','#'],['ki','#ki'],['verlauf','#verlauf']].map(([k,h])=>'<a href="'+h+'" data-ziel="'+k+'"'+(a===k?' aria-current="page"':'')+'>'+kt('tab'+k[0].toUpperCase()+k.slice(1).replace('stress','Stress'))+'</a>').join('');
 leiste.innerHTML=[['stress','#'],['ki','#ki'],['verlauf','#verlauf'],['konto','#konto']].map(([k,h])=>'<a href="'+h+'" data-ziel="'+k+'"'+(a===k?' aria-current="page"':'')+'>'+SVG[k]+'<span>'+kt('tab'+k[0].toUpperCase()+k.slice(1))+'</span></a>').join('');
}
function aktiv(){const h=location.hash.replace('#','');return ['ki','verlauf','konto'].includes(h)?h:'stress'}
if(kopf){kopf.insertBefore(tabs,werkzeuge||null);document.body.append(leiste);document.body.classList.add('mit-leiste')}
/* "#" als Ziel fuer Marktstress: ohne Rest-Raute in der Adresse, Zurueck-Taste bleibt nutzbar */
function navKlick(e){const l=e.target.closest('a[data-ziel]');if(!l||e.metaKey||e.ctrlKey||e.shiftKey)return;
 if(l.dataset.ziel==='stress'){e.preventDefault();if(aktiv()!=='stress'){history.pushState(null,'',location.pathname+location.search);route();window.scrollTo({top:0})}else window.scrollTo({top:0,behavior:'smooth'})}}
leiste.addEventListener('click',navKlick);tabs.addEventListener('click',navKlick);

/* ---------- KI-Ansicht ---------- */
function ansichtAnlegen(){
 ansicht=document.createElement('section');ansicht.id='ki-ansicht';ansicht.className='ki-ansicht';ansicht.hidden=true;ansicht.setAttribute('aria-labelledby','ki-titel');
 (kopf?kopf.after(ansicht):document.body.prepend(ansicht));
 ansicht.addEventListener('click',klick);ansicht.addEventListener('submit',e=>{e.preventDefault();const i=$('#ki-eingabe');if(i&&i.value.trim()){fragen(i.value);}});
 ansicht.addEventListener('input',e=>{if(e.target.id==='ki-eingabe')st.notiz=e.target.value});
}
function restText(){if(st.rest==null)return '';return st.rest<=0?kt('rest0'):st.rest===1?kt('rest1'):kt('rest').replace('{n}',st.rest)}
function eingabeHtml(){
 if(!angemeldet())return '<div class="ki-unten ki-unten-aus"><button type="button" class="primary ki-anmelden" data-ki="anmelden">'+esc(kt('anmelden'))+'</button><p class="ki-hinweis">'+esc(kt('hinweis'))+'</p></div>';
 const leer=st.rest!=null&&st.rest<=0;
 return '<div class="ki-unten"><form class="ki-form" id="ki-form"><label class="sr-only" for="ki-eingabe">'+esc(kt('platzhalter'))+'</label>'
  +'<input id="ki-eingabe" type="text" maxlength="300" autocomplete="off" enterkeyhint="send" placeholder="'+esc(kt('platzhalter'))+'" value="'+esc(st.notiz)+'"'+(leer||st.busy?' disabled':'')+'>'
  +'<button type="submit" class="ki-senden" aria-label="'+esc(kt('senden'))+'"'+(leer||st.busy?' disabled':'')+'>'+SVG.pfeil+'</button></form>'
  +'<p class="ki-hinweis">'+esc(kt('hinweis'))+(restText()?' · <span class="ki-rest">'+esc(restText())+'</span>':'')+'</p></div>';
}
function frageText(f){const w=wert();return (f[sp()]||f.de).replace('{wert}',w==null?'…':w)}
function gruppenHtml(){
 return '<div class="ki-gruppen" role="list">'+KI_FRAGEN.map(g=>'<div class="ki-gruppe" role="listitem"><h3>'+esc(g[sp()]||g.de)+'</h3>'
  +g.fragen.map(f=>{const q=frageText(f);return '<button type="button" class="ki-frage" data-frage="'+esc(q)+'">'+esc(q)+'</button>'}).join('')+'</div>').join('')+'</div>';
}
function startHtml(){
 const w=wert();
 return '<div class="ki-start"><canvas class="ki-kugel" aria-hidden="true"></canvas>'
  +'<p class="eyebrow ki-eyebrow">'+esc(angemeldet()&&w!=null?kt('eyebrowWert').replace('{w}',w):kt('eyebrow'))+'</p>'
  +'<h2 id="ki-titel" tabindex="-1">'+esc(kt('titel'))+'</h2><p class="ki-unter">'+esc(angemeldet()?kt('unter'):kt('ausgeloggt'))+'</p>'
  +gruppenHtml()+'</div>';
}
function md(text){return String(text||'').split(/\n\s*\n/).map(b=>b.trim()?'<p>'+esc(b.trim()).replace(/\*\*(.+?)\*\*/g,'$1').replace(/\n/g,' ')+'</p>':'').join('')}
function gespraechHtml(){
 const w=wert();
 return '<div class="ki-gespraech"><div class="ki-kopf"><canvas class="ki-kugel-klein" aria-hidden="true"></canvas><span class="ki-kopf-text" id="ki-titel" tabindex="-1">'+esc(w!=null?kt('kopf').replace('{w}',w):kt('kopfOhne'))+'</span>'
  +'<button type="button" class="ki-neu" data-ki="neu">'+esc(kt('neu'))+'</button></div>'
  +'<div class="ki-nachrichten" role="log" aria-live="polite" aria-relevant="additions">'+st.gespraech.map(nachrichtHtml).join('')
  +(st.busy?'<p class="ki-denkt" role="status">'+esc(kt('denkt'))+'</p>':'')+'</div></div>';
}
function nachrichtHtml(m,i){
 if(m.rolle==='du')return '<div class="ki-du"><span class="sr-only">'+esc(kt('du'))+': </span>'+esc(m.text)+'</div>';
 if(m.rolle==='fehler')return '<div class="ki-fehler" role="alert">'+esc(kt(m.text))+(m.text==='fLogin'?' <button type="button" class="text-button" data-ki="anmelden">'+esc(kt('fLoginKnopf'))+'</button>':'')+'</div>';
 const letzte=i===st.gespraech.length-1;
 return '<article class="ki-antwort"><span class="sr-only">'+esc(kt('ki'))+': </span>'+md(m.text)+(m.belege?belegHtml(m.belege):'')
  +(letzte&&!st.busy&&m.folge&&m.folge.length?'<div class="ki-folge" aria-label="'+esc(kt('weiter'))+'">'+m.folge.map(q=>'<button type="button" class="ki-frage ki-chip" data-frage="'+esc(q)+'">'+esc(q)+'</button>').join('')+'</div>':'')+'</article>';
}
/* Beleg: Verlaufsausschnitt (Reihe liefert der Server: dieselben Marktstress-Werte, auf die sich die Antwort stuetzt),
   markierter Tag, Teilwerte der drei Blickwinkel */
function zeitraumText(a,b){const da=new Date(Date.parse(a+'T12:00:00Z')),db=new Date(Date.parse(b+'T12:00:00Z')),L=sp()==='en'?'en-US':'de-DE',o={timeZone:'UTC'};
 if(da.getUTCFullYear()===db.getUTCFullYear()&&da.getUTCMonth()===db.getUTCMonth())return da.toLocaleDateString(L,Object.assign({month:'long',year:'numeric'},o));
 return kt('belegTitel').replace('{a}',datumKurz(a)).replace('{b}',datumKurz(b))}
function belegHtml(b){
 let s='<div class="ki-beleg">';
 const p=(b.reihe||[]).filter(q=>q&&q[1]!=null);
 if(p.length>1){
  const W=300,H=64,a=Date.parse(p[0][0]),z=Date.parse(p[p.length-1][0]),x=d=>4+(Date.parse(d)-a)/(z-a||1)*(W-8),y=w=>4+(100-w)*(H-8)/100;
  const mk=p.find(q=>q[0]===b.markiert)||p[p.length-1];
  s+='<figure class="ki-spark"><figcaption>'+esc(sp()==='en'?'Market stress, ':'Marktstress ')+esc(zeitraumText(p[0][0],p[p.length-1][0]))+' · '+esc(kt('belegTag').replace('{w}',mk[1]).replace('{d}',datumLang(mk[0])))+'</figcaption>'
   +'<div class="ki-spark-flaeche"><svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" aria-hidden="true"><line x1="0" x2="'+W+'" y1="'+y(50)+'" y2="'+y(50)+'" class="ki-spark-mitte"/><polyline points="'+p.map(q=>x(q[0]).toFixed(1)+','+y(q[1]).toFixed(1)).join(' ')+'"/>'
   +'<line class="ki-spark-tag" x1="'+x(mk[0]).toFixed(1)+'" x2="'+x(mk[0]).toFixed(1)+'" y1="0" y2="'+H+'"/></svg>'
   +'<span class="ki-spark-punkt" style="left:'+(x(mk[0])/W*100).toFixed(2)+'%;top:'+(y(mk[1])/H*100).toFixed(2)+'%"></span></div></figure>';
 }
 const tw=b.teilwerte;
 if(tw&&Object.keys(tw).length)s+='<p class="ki-teil-titel">'+esc(kt('teilwerte').replace('{d}',datumLang(b.markiert||b.bis)))+'</p><div class="ki-teile">'+[['volatility','vol'],['price','preis'],['positioning','stimmung']].filter(([k])=>tw[k]!=null).map(([k,l])=>'<span class="ki-teil"><span>'+esc(kt(l))+'</span><b>'+Math.round(tw[k])+'</b></span>').join('')+'</div>';
 return s+'</div>';
}
/* Folgefragen: zwei aus dem Katalog, die noch nicht gestellt wurden; zuerst aus der Gruppe der letzten Frage */
function folgefragen(frage){
 const gestellt=new Set(st.gespraech.filter(m=>m.rolle==='du').map(m=>m.text));
 const alle=KI_FRAGEN.map(g=>g.fragen.map(frageText));
 let gi=alle.findIndex(g=>g.includes(frage));if(gi<0)gi=st.gespraech.filter(m=>m.rolle==='du').length%alle.length;
 const reihe=[...alle[gi],...alle[(gi+1)%alle.length],...alle[(gi+2)%alle.length]];
 return reihe.filter(q=>!gestellt.has(q)&&q!==frage).slice(0,2);
}
function zeichnen(fokus){
 if(!ansicht)return;
 const start=!st.gespraech.length;
 ansicht.classList.toggle('ki-ist-start',start);ansicht.classList.toggle('ki-ist-gespraech',!start);
 ansicht.innerHTML='<div class="ki-innen">'+(start?startHtml():gespraechHtml())+'</div>'+eingabeHtml();
 grosseKugel=null;kleineKugel=null;
 const g=ansicht.querySelector('.ki-kugel'),k=ansicht.querySelector('.ki-kugel-klein');
 if(g)grosseKugel=kugel(g,mobil()?{punkte:56,grenze:.58,impulse:true,schein:true,radius:.4}:{punkte:92,grenze:.45,impulse:true,schein:true,radius:.4});
 if(k){kleineKugel=kugel(k,{punkte:36,grenze:.7,radius:.44,linie:.6,punkt:.5,punktZu:.35});kleineKugel.tempo(st.busy?6:1);k.classList.toggle('denkt',st.busy)}
 platzUnten();
 if(fokus==='eingabe')$('#ki-eingabe')?.focus({preventScroll:true});else if(fokus==='titel')$('#ki-titel')?.focus({preventScroll:true});
}
function nachUnten(weich){if(!haftUnten)return;requestAnimationFrame(()=>{const m=ansicht&&ansicht.querySelector('.ki-nachrichten>:last-child');if(m){const r=m.getBoundingClientRect(),unten=platzUntenPx();if(r.top>innerHeight-unten-60||r.bottom>innerHeight-unten)window.scrollBy({top:Math.min(r.top-90,r.bottom-(innerHeight-unten)+16),behavior:weich?'smooth':'auto'})}})}
addEventListener('scroll',()=>{if(aktiv()!=='ki')return;haftUnten=innerHeight+scrollY>=document.documentElement.scrollHeight-140},{passive:true});
/* Uebergang: grosse Kugel schrumpft zum Symbol oben links */
function schrumpfen(){
 const g=ansicht.querySelector('.ki-kugel');if(!g||matchMedia('(prefers-reduced-motion: reduce)').matches||!g.animate)return null;
 const r=g.getBoundingClientRect(),klon=g.cloneNode();klon.className='ki-kugel-flug';
 const c=klon.getContext('2d');c.drawImage(g,0,0);document.body.append(klon);
 Object.assign(klon.style,{left:r.left+'px',top:r.top+'px',width:r.width+'px',height:r.height+'px'});
 return ()=>{const k=ansicht.querySelector('.ki-kugel-klein');if(!k){klon.remove();return}const z=k.getBoundingClientRect();
  k.style.opacity='0';
  klon.animate([{transform:'translate(0,0) scale(1)',opacity:1},{transform:'translate('+(z.left-r.left)+'px,'+(z.top-r.top)+'px) scale('+(z.width/r.width)+')',opacity:.9}],{duration:520,easing:'cubic-bezier(.3,.7,.2,1)'}).onfinish=()=>{klon.remove();k.style.opacity=''}};
}
async function restLaden(){
 if(st.restGeladen||!angemeldet())return;st.restGeladen=true;
 try{const k=await api('konto');if(k&&k.ki&&k.ki.tag){st.rest=Math.max(0,k.ki.tag-k.ki.heute);if(aktiv()==='ki'){const r=ansicht.querySelector('.ki-hinweis');if(r)zeichnenUnten()}}}catch{st.restGeladen=false}
}
function zeichnenUnten(){const u=ansicht.querySelector('.ki-unten');if(!u)return;const fokus=document.activeElement&&document.activeElement.id==='ki-eingabe';u.outerHTML=eingabeHtml();platzUnten();if(fokus)$('#ki-eingabe')?.focus({preventScroll:true})}
async function fragen(text){
 text=String(text||'').trim().slice(0,300);if(!text||st.busy)return;
 if(!angemeldet()){$('#account-login')?.click();return}
 const flug=!st.gespraech.length?schrumpfen():null;
 const verlaufMsgs=st.gespraech.filter(m=>m.rolle==='ki').slice(-3).length?st.gespraech.reduce((acc,m,i,arr)=>{if(m.rolle==='du'&&arr[i+1]&&arr[i+1].rolle==='ki')acc.push({role:'user',content:m.text},{role:'assistant',content:arr[i+1].text});return acc},[]).slice(-6):[];
 st.gespraech.push({rolle:'du',text});st.busy=true;st.notiz='';haftUnten=true;
 zeichnen('eingabe');if(flug)flug();nachUnten(true);
 let antwort=null;
 try{
  const tok=IT.token?await IT.token():null;
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json',...(tok?{Authorization:'Bearer '+tok}:{})},body:JSON.stringify({frage:text,verlauf:verlaufMsgs,sprache:sp()})});
  if(r.status===401){antwort={rolle:'fehler',text:'fLogin'}}
  else if(r.status===429){antwort={rolle:'fehler',text:'fLimit'};st.rest=0}
  else if(r.status===503){antwort={rolle:'fehler',text:'fAus'}}
  else if(!r.ok){antwort={rolle:'fehler',text:'fNetz'}}
  else{const d=await r.json();if(d.rest!=null)st.rest=d.rest;
   antwort={rolle:'ki',text:String(d.antwort||''),belege:d.belege||null,folge:folgefragen(text)}}
 }catch{antwort={rolle:'fehler',text:'fNetz'}}
 st.busy=false;st.gespraech.push(antwort);
 if(aktiv()==='ki'){zeichnen(document.activeElement&&document.activeElement.id==='ki-eingabe'?'eingabe':null);nachUnten(true)}
}
function klick(e){
 const f=e.target.closest('[data-frage]');
 if(f){if(!angemeldet()){$('#account-login')?.click();return}st.notiz=f.dataset.frage;const i=$('#ki-eingabe');if(i){i.value=st.notiz;i.focus();i.setSelectionRange(i.value.length,i.value.length)}return}
 const b=e.target.closest('[data-ki]');if(!b)return;
 if(b.dataset.ki==='anmelden'){$('#account-login')?.click();return}
 if(b.dataset.ki==='neu'){st.gespraech=[];st.notiz='';haftUnten=true;zeichnen('titel');window.scrollTo({top:0})}
}

/* ---------- Mobil: Eingabe ueber der Tastatur, Leiste unten ---------- */
function platzUntenPx(){const u=ansicht&&ansicht.querySelector('.ki-unten');return u?u.getBoundingClientRect().height+(mobil()?leiste.getBoundingClientRect().height:0):0}
function platzUnten(){
 if(!ansicht)return;const u=ansicht.querySelector('.ki-unten');if(!u)return;
 const vv=window.visualViewport,tast=vv?Math.max(0,innerHeight-vv.height-vv.offsetTop):0,offen=tast>80;
 document.body.classList.toggle('ki-tastatur',offen&&aktiv()==='ki');
 u.style.bottom=mobil()?(offen?tast+'px':''):'';
 ansicht.style.paddingBottom=(u.getBoundingClientRect().height+16)+'px';
}
if(window.visualViewport){visualViewport.addEventListener('resize',()=>{platzUnten();nachUnten(false)});visualViewport.addEventListener('scroll',platzUnten)}
addEventListener('resize',platzUnten);

/* ---------- Routing: Marktstress (ohne Raute), #ki, #verlauf, #konto ---------- */
const scrollMerk={};let letzte=null;
function route(){
 const a=aktiv();
 if(letzte&&letzte!==a)scrollMerk[letzte]=window.scrollY;
 ['ki','verlauf','konto'].forEach(k=>document.body.classList.toggle('ansicht-'+k,a===k));
 document.body.classList.toggle('ansicht-neben',a!=='stress');
 if(!ansicht)ansichtAnlegen();
 ansicht.hidden=a!=='ki';navRender();
 IT.verlaufAnsicht&&IT.verlaufAnsicht[a==='verlauf'?'zeigen':'verbergen']();
 IT.kontoAnsicht&&IT.kontoAnsicht[a==='konto'?'zeigen':'verbergen']();
 if(a==='ki'){zeichnen(st.gespraech.length?null:'titel');restLaden();window.scrollTo({top:st.gespraech.length?document.documentElement.scrollHeight:0});haftUnten=true}
 else{document.body.classList.remove('ki-tastatur');
  if(letzte!==a){window.scrollTo({top:a==='stress'?(scrollMerk.stress||0):0});
   if(letzte){const h=a==='verlauf'?$('#verlauf-ansicht-titel'):a==='konto'?$('#konto-ansicht-titel'):null;h&&h.focus({preventScroll:true})}}}
 letzte=a;
}
IT.route=route;IT.aktiveAnsicht=aktiv;
addEventListener('popstate',route);
addEventListener('hashchange',route);
document.addEventListener('click',e=>{
 const l=e.target.closest('[data-ki-login]');if(l){$('#account-login')?.click();return}
 const q=e.target.closest('[data-ki-frage]');if(!q)return;e.preventDefault();
 st.notiz=q.dataset.kiFrage;if(location.hash!=='#ki')location.hash='ki';else zeichnen('eingabe');
 setTimeout(()=>{const i=$('#ki-eingabe');if(i){i.focus({preventScroll:true});i.setSelectionRange(i.value.length,i.value.length)}},80);
});

/* ---------- "Frag die KI dazu" und schmale KI-Zeile neben dem Wert ---------- */
const spalte=$('.score-column'),erst=$('.first-look'),modul=$('#subscribe-module');
const fragLink=document.createElement('p');fragLink.className='ki-frag-link';
if(modul)modul.before(fragLink);
const zeile=document.createElement('form');zeile.className='ki-zeile';zeile.id='ki-zeile';
if(erst)erst.append(zeile);
zeile.addEventListener('submit',e=>{e.preventDefault();const i=zeile.querySelector('input');st.notiz=i.value.trim()||kt('frageWert').replace('{w}',wert()??'');i.value='';location.hash='ki';
 setTimeout(()=>{const k=$('#ki-eingabe');if(k){k.focus({preventScroll:true});k.setSelectionRange(k.value.length,k.value.length)}},80)});
function extrasRender(){
 const w=IT.view&&IT.view.rounded;
 fragLink.innerHTML=w!=null?'<a href="#ki" class="ki-frag" data-ki-frage="'+esc(kt('frageWert').replace('{w}',angemeldet()&&wert()!=null?wert():w))+'">'+esc(kt('fragKi'))+'</a>':'';
 zeile.hidden=!angemeldet();
 zeile.innerHTML='<label class="sr-only" for="ki-zeile-eingabe">'+esc(kt('zeileLabel'))+'</label><input id="ki-zeile-eingabe" type="text" maxlength="300" autocomplete="off" enterkeyhint="go" placeholder="'+esc(kt('zeile'))+'"><button type="submit" aria-label="'+esc(kt('zumKi'))+'">'+SVG.pfeil+'</button>';
}
IT.kiFrageEreignis=name=>kt('frageEreignis').replace('{n}',name);
IT.kiText=kt;
document.addEventListener('investtimer:update',()=>{extrasRender();navRender();st.restGeladen=false;if(aktiv()==='ki'){zeichnen();restLaden()}});
new MutationObserver(()=>{extrasRender();navRender();if(aktiv()==='ki')zeichnen()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
extrasRender();route();
})();
