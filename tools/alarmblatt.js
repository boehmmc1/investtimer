/* Alarme (Auftrag 20.11.2026): Karte auf der Startseite, Blatt "Alarm einstellen/bearbeiten", Liste "Deine Alarme",
   hoechstens zwei Marken am Bogen. Zustaende ueberall: bereit (armed), ausgeloest (triggered), pausiert (paused).
   Grenze 3 Alarme je Richtung (Server prueft mit). Aktueller Wert aus derselben Quelle wie Startseite/Verlauf (IT.live). */
(()=>{
/* Platz fuer die Alarm-Karte: direkt unter dem Einordnungssatz, vor der KI-Karte */
(()=>{if($('#alarm-karte'))return;const d=document.createElement('div');d.id='alarm-karte';d.className='alarm-karte alarm-zeile';const ki=$('.ki-bruecke-start'),as=$('.assessment');if(ki)ki.before(d);else if(as)as.after(d)})();
const AT={de:{setzen:'Alarm setzen',eins:'1 ALARM',mehr:'{n} ALARME',naechster:'Nächster: {r} {x}',noch:'Noch {n} Punkte',noch1:'Noch 1 Punkt',
  unten:' · nach unten: unter {y}',oben:' · nach oben: über {y}',alleAus:'Alle Alarme ausgelöst',alleAusText:'Melden sich wieder, wenn der Wert zurückkommt',
  ueber:'über',unter:'unter',titelNeu:'Alarm einstellen',titelEdit:'Alarm bearbeiten',jetzt:'Jetzt {w}',alarmUeber:'Alarm über {x}',alarmUnter:'Alarm unter {x}',
  steigt:'steigt über',faellt:'fällt unter',richtung:'Richtung',schwelle:'Schwelle',minus:'Schwelle senken',plus:'Schwelle erhöhen',
  hinweisUeber:'Noch {n}. Du bekommst eine Nachricht, sobald der Marktstress über {x} steigt.',hinweisUnter:'Noch {n}. Du bekommst eine Nachricht, sobald der Marktstress unter {x} fällt.',
  punkte:'{n} Punkte',punkt:'1 Punkt',
  schonUeber:'Der Marktstress liegt schon über {x}. Der Alarm meldet sich, wenn der Wert zurückkommt und die Schwelle erneut überquert.',
  schonUnter:'Der Marktstress liegt schon unter {x}. Der Alarm meldet sich, wenn der Wert zurückkommt und die Schwelle erneut überquert.',
  vollUeber:'Du hast schon 3 Alarme für steigenden Marktstress. Ändere oder lösch einen.',vollUnter:'Du hast schon 3 Alarme für fallenden Marktstress. Ändere oder lösch einen.',
  kanaele:'Benachrichtigung',push:'Push',email:'E-Mail',mailAn:'E-Mails gehen an {e}.',speichern:'Alarm speichern',loeschen:'Alarm löschen',loeschenFrage:'Diesen Alarm wirklich löschen?',
  loeschenJa:'Löschen',abbrechen:'Abbrechen',schliessen:'Schließen',doppelt:'Diesen Alarm gibt es schon.',fehler:'Das hat nicht geklappt. Bitte versuch es noch einmal.',
  pushFrage:'Mitteilungen sind auf diesem Gerät noch nicht erlaubt.',pushErlauben:'Mitteilungen erlauben',pushIos:'Auf dem iPhone kommen Mitteilungen nur in der installierten App (Teilen → „Zum Home-Bildschirm“).',
  pushBlockiert:'Mitteilungen sind für investtimer.net in den Einstellungen des Browsers blockiert.',gespeichert:'Alarm gespeichert.',
  liste:'Deine Alarme',jetztListe:'Marktstress jetzt {w}',steigtGr:'WENN ER STEIGT',faelltGr:'WENN ER FÄLLT',zeileUeber:'über {x}',zeileUnter:'unter {x}',nochKurz:'noch {n}',genau:'Genau auf der Schwelle',genauKurz:'genau auf der Schwelle',
  ausgeloestN:'{n} ausgelöst',ausgeloestAm:'ausgelöst am {d}',pausiert:'pausiert',neu:'+ Neuer Alarm',beideVoll:'Höchstens 3 Alarme je Richtung.',
  erklUeber:'Ausgelöst am {d}. Meldet sich wieder, wenn der Wert unter {x} fällt und danach erneut steigt.',
  erklUnter:'Ausgelöst am {d}. Meldet sich wieder, wenn der Wert über {x} steigt und danach erneut fällt.',
  erklUeberNeu:'Schwelle beim Anlegen schon überschritten. Meldet sich, wenn der Wert unter {x} fällt und danach erneut steigt.',
  erklUnterNeu:'Schwelle beim Anlegen schon unterschritten. Meldet sich, wenn der Wert über {x} steigt und danach erneut fällt.',
  mitteilungen:'Mitteilungen auf diesem Gerät',schild:'{r} {x} · noch {n}',markeAria:'Alarm {r} {x}'},
 en:{setzen:'Set an alert',eins:'1 ALERT',mehr:'{n} ALERTS',naechster:'Next: {r} {x}',noch:'{n} points to go',noch1:'1 point to go',
  unten:' · on the way down: below {y}',oben:' · on the way up: above {y}',alleAus:'All alerts triggered',alleAusText:'They’ll notify you again once the score comes back',
  ueber:'above',unter:'below',titelNeu:'Set alert',titelEdit:'Edit alert',jetzt:'Now {w}',alarmUeber:'Alert above {x}',alarmUnter:'Alert below {x}',
  steigt:'rises above',faellt:'falls below',richtung:'Direction',schwelle:'Threshold',minus:'Lower threshold',plus:'Raise threshold',
  hinweisUeber:'{n} to go. You’ll get a message as soon as market stress rises above {x}.',hinweisUnter:'{n} to go. You’ll get a message as soon as market stress falls below {x}.',
  punkte:'{n} points',punkt:'1 point',
  schonUeber:'Market stress is already above {x}. The alert will notify you once the score comes back and crosses the threshold again.',
  schonUnter:'Market stress is already below {x}. The alert will notify you once the score comes back and crosses the threshold again.',
  vollUeber:'You already have 3 alerts for rising market stress. Change or delete one.',vollUnter:'You already have 3 alerts for falling market stress. Change or delete one.',
  kanaele:'Notify me by',push:'Push',email:'Email',mailAn:'Emails go to {e}.',speichern:'Save alert',loeschen:'Delete alert',loeschenFrage:'Delete this alert?',
  loeschenJa:'Delete',abbrechen:'Cancel',schliessen:'Close',doppelt:'You already have this alert.',fehler:'That didn’t work. Please try again.',
  pushFrage:'Notifications aren’t allowed on this device yet.',pushErlauben:'Allow notifications',pushIos:'On iPhone, notifications only work in the installed app (Share → “Add to Home Screen”).',
  pushBlockiert:'Notifications for investtimer.net are blocked in your browser settings.',gespeichert:'Alert saved.',
  liste:'Your alerts',jetztListe:'Market stress now {w}',steigtGr:'IF IT RISES',faelltGr:'IF IT FALLS',zeileUeber:'above {x}',zeileUnter:'below {x}',nochKurz:'{n} to go',genau:'Right at the threshold',genauKurz:'right at the threshold',
  ausgeloestN:'{n} triggered',ausgeloestAm:'triggered {d}',pausiert:'paused',neu:'+ New alert',beideVoll:'At most 3 alerts per direction.',
  erklUeber:'Triggered on {d}. Will notify you again once the score falls below {x} and then rises again.',
  erklUnter:'Triggered on {d}. Will notify you again once the score rises above {x} and then falls again.',
  erklUeberNeu:'Threshold was already crossed when you set it. Will notify you once the score falls below {x} and then rises again.',
  erklUnterNeu:'Threshold was already crossed when you set it. Will notify you once the score rises above {x} and then falls again.',
  mitteilungen:'Notifications on this device',schild:'{r} {x} · {n} to go',markeAria:'Alert {r} {x}'}};
const en=()=>document.documentElement.lang==='en',at=k=>AT[en()?'en':'de'][k];
const JE=3,GRENZEN=[20,40,60,80];
const SVG={glocke:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>',
 pfeil:'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m8 5 5 5-5 5"/></svg>',hoch:'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 15V5M6 9l4-4 4 4"/></svg>',
 runter:'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 5v10M6 11l4 4 4-4"/></svg>',haken:'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 10.5 3.2 3L15 7"/></svg>',
 zu:'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5 5 15"/></svg>'};
const angemeldet=()=>!!(IT.member&&(IT.session||(IT.emailVonSitzung&&IT.emailVonSitzung())));
/* Eine Quelle fuer den aktuellen Wert (wie Startseite, Verlauf, KI) */
const wert=()=>{const v=IT.member&&IT.live?IT.live:null;return v&&v.rounded!=null?v.rounded:null};
const datumKurz=d=>new Date(Date.parse(d+'T12:00:00Z')).toLocaleDateString(en()?'en-US':'de-DE',{day:'numeric',month:'short',timeZone:'UTC'});
let daten=null,laedt=null;
async function laden(neu){
 if(!angemeldet()){daten=null;return null}
 if(daten&&!neu)return daten;if(laedt)return laedt;
 laedt=api('alarme').then(d=>{daten=d;laedt=null;melden();return d}).catch(()=>{laedt=null;return daten});return laedt;
}
function melden(){IT.alarmDaten=daten;document.dispatchEvent(new CustomEvent('investtimer:alarme',{detail:daten}));karte();marken()}
const liste=()=>(daten&&daten.alarme)||[];
const bereit=()=>liste().filter(a=>a.zustand==='bereit');
/* naechster bereiter Alarm je Richtung bzw. insgesamt (kleinster Abstand zum aktuellen Wert) */
function naechste(){
 const w=wert(),b=bereit();if(w==null)return {};
 const ab=a=>Math.abs(a.schwelle-w);
 const ueber=b.filter(a=>a.richtung==='ueber'&&a.schwelle>=w).sort((x,y)=>ab(x)-ab(y))[0]||null;
 const unter=b.filter(a=>a.richtung==='unter'&&a.schwelle<=w).sort((x,y)=>ab(x)-ab(y))[0]||null;
 const alle=[ueber,unter].filter(Boolean).sort((x,y)=>ab(x)-ab(y));
 return {ueber,unter,erster:alle[0]||null,zweiter:alle[1]||null};
}
const punkteText=n=>n===0?at('genau'):n===1?at('noch1'):at('noch').replace('{n}',n);

/* ---------- Karte auf der Startseite ---------- */
function karte(){
 const k=$('#alarm-karte');if(!k)return;
 const w=wert(),l=liste();
 if(!angemeldet()||!l.length){
  k.className='alarm-karte alarm-zeile';
  k.innerHTML='<button type="button" class="alarm-karte-knopf" data-alarm="'+(angemeldet()?'neu':'login')+'"><span class="alarm-glocke">'+SVG.glocke+'</span><span class="alarm-karte-titel">'+esc(at('setzen'))+'</span><span class="alarm-karte-pfeil">'+SVG.pfeil+'</span></button>';
  return;
 }
 const n=naechste(),r=a=>at(a.richtung==='ueber'?'ueber':'unter');
 let titel,unter;
 if(n.erster&&w!=null){
  titel=at('naechster').replace('{r}',r(n.erster)).replace('{x}',n.erster.schwelle);
  unter=punkteText(Math.abs(n.erster.schwelle-w))+(n.zweiter?at(n.zweiter.richtung==='unter'?'unten':'oben').replace('{y}',n.zweiter.schwelle):'');
 }else{titel=at('alleAus');unter=at('alleAusText')}
 k.className='alarm-karte alarm-voll';
 k.innerHTML='<button type="button" class="alarm-karte-knopf" data-alarm="liste"><span class="alarm-glocke rund">'+SVG.glocke+'</span>'
  +'<span class="alarm-karte-text"><span class="alarm-karte-label">'+esc(l.length===1?at('eins'):at('mehr').replace('{n}',l.length))+'</span>'
  +'<span class="alarm-karte-titel">'+esc(titel)+'</span><span class="alarm-karte-unter">'+esc(unter)+'</span></span><span class="alarm-karte-pfeil">'+SVG.pfeil+'</span></button>';
}

/* ---------- Blatt (Bottom-Sheet mobil, Dialog Desktop) ---------- */
const blatt=document.createElement('dialog');blatt.className='alarm-blatt';blatt.setAttribute('aria-labelledby','alarm-blatt-titel');document.body.append(blatt);
let zustand=null,oeffner=null,ringAnim=0,ringIst=null;
function zu(){if(blatt.open)blatt.close()}
/* Logo (Nachtrag L): ungespeicherte Aenderung im Blatt erkennen, Blatt von aussen schliessen */
IT.alarmBlattGeaendert=()=>!!(blatt.open&&zustand&&zustand.start!==[zustand.richtung,zustand.schwelle,zustand.push,zustand.email].join());
IT.alarmBlattZu=zu;
blatt.addEventListener('close',()=>{document.body.classList.remove('alarm-blatt-offen');oeffner&&oeffner.isConnected&&oeffner.focus({preventScroll:true})});
blatt.addEventListener('click',e=>{if(e.target===blatt){const r=blatt.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)zu()}});
function zeigen(html,fokus){
 blatt.innerHTML='<div class="blatt-griff" aria-hidden="true"></div><button type="button" class="blatt-zu" data-alarm="zu" aria-label="'+esc(at('schliessen'))+'">'+SVG.zu+'</button>'+html;
 if(!blatt.open){blatt.showModal();document.body.classList.add('alarm-blatt-offen')}
 (blatt.querySelector(fokus||'h2')||blatt).focus({preventScroll:true});
}
function vorbelegen(richtung){
 const w=wert()??50;
 if(richtung==='ueber'){const g=GRENZEN.find(x=>x>w);return g??Math.min(99,Math.max(w+1,90))}
 const g=GRENZEN.slice().reverse().find(x=>x<w);return g??Math.max(1,Math.min(w-1,10));
}
const zaehl=r=>liste().filter(a=>a.richtung===r).length;
function voll(r){return zaehl(r)>=JE&&!(zustand&&zustand.alarm&&zustand.alarm.richtung===r)}
function oeffneBlatt(alarm,von){
 oeffner=von||document.activeElement;
 const kanal=alarm?alarm.kanal:(IT.alarmKanalStandard||'push');
 zustand={alarm:alarm||null,richtung:alarm?alarm.richtung:(voll('ueber')&&!voll('unter')?'unter':'ueber'),schwelle:0,
  push:kanal!=='email',email:kanal!=='push',frage:false,fehler:'',pushHinweis:''};
 zustand.schwelle=alarm?alarm.schwelle:vorbelegen(zustand.richtung);ringIst=null;
 zustand.start=[zustand.richtung,zustand.schwelle,zustand.push,zustand.email].join();
 renderBlatt();
}
function bogenPunkt(v,r){const a=(180+Math.max(0,Math.min(100,v))*1.8)*Math.PI/180;return [100+r*Math.cos(a),100+r*Math.sin(a)]}
function miniBogen(){
 const w=wert(),f=w!=null?ITStufe.farbe(w):'#6e7b74',[px,py]=bogenPunkt(w??0,80),[rx,ry]=bogenPunkt(ringIst??zustand.schwelle,80);
 const wp=w==null?0:w;
 return '<div class="mini-bogen"><svg viewBox="0 0 200 112" aria-hidden="true"><path class="mb-spur" d="M20 100A80 80 0 0 1 180 100"/>'
  +'<path class="mb-wert" d="M20 100A80 80 0 0 1 180 100" pathLength="100" style="stroke:'+f+';stroke-dasharray:'+wp+' 100"/>'
  +'<circle class="mb-ring" r="7" cx="'+rx.toFixed(1)+'" cy="'+ry.toFixed(1)+'"/>'
  +(w!=null?'<circle class="mb-punkt" r="6" cx="'+px.toFixed(1)+'" cy="'+py.toFixed(1)+'" style="fill:'+f+'"/>':'')+'</svg>'
  +'<div class="mb-mitte"><span class="mb-jetzt">'+esc(at('jetzt').replace('{w}',w??'–'))+'</span><span class="mb-alarm">'+esc(at(zustand.richtung==='ueber'?'alarmUeber':'alarmUnter').replace('{x}',zustand.schwelle))+'</span></div></div>';
}
function hinweis(){
 const r=zustand.richtung,x=zustand.schwelle,w=wert();
 if(voll(r))return {text:at(r==='ueber'?'vollUeber':'vollUnter'),art:'voll'};
 if(w==null)return {text:'',art:''};
 const schon=r==='ueber'?w>x:w<x;
 if(schon)return {text:at(r==='ueber'?'schonUeber':'schonUnter').replace('{x}',x),art:'schon'};
 const n=Math.abs(x-w),pk=n===1?at('punkt'):at('punkte').replace('{n}',n);
 return {text:at(r==='ueber'?'hinweisUeber':'hinweisUnter').replace('{n}',pk).replace('{x}',x),art:''};
}
function renderBlatt(fokus){
 const z=zustand,h=hinweis(),mail=(IT.emailVonSitzung&&IT.emailVonSitzung())||'';
 const chip=(k,an)=>'<button type="button" class="kanal-chip" data-kanal="'+k+'" aria-pressed="'+an+'">'+(an?SVG.haken:'')+'<span>'+esc(at(k))+'</span></button>';
 const loesch=z.alarm?(z.frage?'<p class="blatt-frage">'+esc(at('loeschenFrage'))+' <button type="button" class="text-button warn" data-alarm="loeschen-ja">'+esc(at('loeschenJa'))+'</button> <button type="button" class="text-button" data-alarm="loeschen-nein">'+esc(at('abbrechen'))+'</button></p>'
  :'<button type="button" class="text-button blatt-loeschen" data-alarm="loeschen">'+esc(at('loeschen'))+'</button>'):'';
 zeigen('<h2 id="alarm-blatt-titel" tabindex="-1">'+esc(at(z.alarm?'titelEdit':'titelNeu'))+'</h2>'+miniBogen()
  +'<div class="blatt-segment" role="group" aria-label="'+esc(at('richtung'))+'"><button type="button" data-richtung="ueber" aria-pressed="'+(z.richtung==='ueber')+'">'+esc(at('steigt'))+'</button><button type="button" data-richtung="unter" aria-pressed="'+(z.richtung==='unter')+'">'+esc(at('faellt'))+'</button></div>'
  +'<div class="blatt-schwelle" role="group" aria-label="'+esc(at('schwelle'))+'"><button type="button" class="rund-knopf" data-schritt="-1" aria-label="'+esc(at('minus'))+'">−</button>'
  +'<output class="blatt-zahl" aria-live="polite">'+z.schwelle+'</output><button type="button" class="rund-knopf" data-schritt="1" aria-label="'+esc(at('plus'))+'">+</button></div>'
  +'<p class="blatt-hinweis'+(h.art?' '+h.art:'')+'" role="status">'+esc(h.text)+'</p>'
  +'<div class="blatt-kanaele" role="group" aria-label="'+esc(at('kanaele'))+'">'+chip('push',z.push)+chip('email',z.email)+'</div>'
  +(z.email&&mail?'<p class="blatt-klein">'+esc(at('mailAn').replace('{e}',mail))+'</p>':'')
  +(z.fehler?'<p class="blatt-fehler" role="alert">'+esc(z.fehler)+'</p>':'')
  +(z.pushHinweis?'<div class="blatt-push" role="status">'+z.pushHinweis+'</div>':'')
  +'<button type="button" class="blatt-speichern" data-alarm="speichern">'+esc(at('speichern'))+'</button>'+loesch,fokus||'#alarm-blatt-titel');
}
/* Ring wandert fluessig zur neuen Schwelle; Zahl und Texte sofort */
function aktualisieren(){
 const z=zustand,zahl=blatt.querySelector('.blatt-zahl'),h=hinweis(),hp=blatt.querySelector('.blatt-hinweis');
 if(zahl)zahl.textContent=z.schwelle;if(hp){hp.textContent=h.text;hp.className='blatt-hinweis'+(h.art?' '+h.art:'')}
 const mb=blatt.querySelector('.mb-alarm');if(mb)mb.textContent=at(z.richtung==='ueber'?'alarmUeber':'alarmUnter').replace('{x}',z.schwelle);
 const ring=blatt.querySelector('.mb-ring');if(!ring)return;
 const ziel=z.schwelle,start=ringIst??ziel,t0=performance.now(),dauer=matchMedia('(prefers-reduced-motion: reduce)').matches?0:160;
 cancelAnimationFrame(ringAnim);
 const schritt=t=>{const k=dauer?Math.min(1,(t-t0)/dauer):1,v=start+(ziel-start)*(1-Math.pow(1-k,3));ringIst=v;const [x,y]=bogenPunkt(v,80);ring.setAttribute('cx',x.toFixed(1));ring.setAttribute('cy',y.toFixed(1));if(k<1)ringAnim=requestAnimationFrame(schritt)};
 ringAnim=requestAnimationFrame(schritt);
}
/* gedrueckt halten = schneller */
let halten=0,haltenZaehl=0;
function schritt(d){zustand.schwelle=Math.max(1,Math.min(99,zustand.schwelle+d));aktualisieren()}
blatt.addEventListener('pointerdown',e=>{const b=e.target.closest('[data-schritt]');if(!b)return;e.preventDefault();const d=Number(b.dataset.schritt);schritt(d);haltenZaehl=0;
 clearTimeout(halten);const weiter=()=>{haltenZaehl++;schritt(d);halten=setTimeout(weiter,haltenZaehl>3?50:120)};halten=setTimeout(weiter,380)});
['pointerup','pointercancel','pointerleave'].forEach(t=>blatt.addEventListener(t,()=>clearTimeout(halten)));
blatt.addEventListener('keydown',e=>{const b=e.target.closest('[data-schritt]');if(b&&(e.key==='Enter'||e.key===' ')){e.preventDefault();schritt(Number(b.dataset.schritt))}});

async function pushPruefen(){
 if(!zustand.push||typeof pushStatus!=='function')return '';
 const s=await pushStatus().catch(()=>'nein');
 if(s==='aktiv')return '';
 if(s==='ios')return '<p>'+esc(at('pushIos'))+'</p>';
 if(s==='blockiert')return '<p>'+esc(at('pushBlockiert'))+'</p>';
 if(s==='aus')return '<p>'+esc(at('pushFrage'))+'</p><button type="button" class="text-button" data-alarm="push-an">'+esc(at('pushErlauben'))+'</button>';
 return '';
}
async function speichern(knopf){
 const z=zustand;if(voll(z.richtung)){z.fehler='';renderBlatt('.blatt-hinweis');return}
 const kanal=z.push&&z.email?'beide':z.email?'email':'push';knopf.disabled=true;knopf.classList.add('laedt');
 try{
  const body={richtung:z.richtung,schwelle:z.schwelle,kanal,sprache:document.documentElement.lang};
  daten=z.alarm?await api('alarme/'+z.alarm.id,{method:'PATCH',body:JSON.stringify(body)}):await api('alarme',{method:'POST',body:JSON.stringify(body)});
  IT.alarmKanalStandard=kanal;melden();
  z.start=[z.richtung,z.schwelle,z.push,z.email].join();
 }catch(x){z.fehler=x==='doppelt'?at('doppelt'):x==='richtung_voll'?at(z.richtung==='ueber'?'vollUeber':'vollUnter'):at('fehler');renderBlatt('.blatt-fehler');return}
 const p=await pushPruefen();
 if(p){z.pushHinweis='<p><b>'+esc(at('gespeichert'))+'</b></p>'+p;z.alarm=liste().find(a=>a.richtung===z.richtung&&a.schwelle===z.schwelle)||z.alarm;renderBlatt('.blatt-push');return}
 zu();typeof toast==='function'&&toast(at('gespeichert'));
}
blatt.addEventListener('click',async e=>{
 const r=e.target.closest('[data-richtung]');
 if(r&&r.dataset.richtung!==zustand.richtung){zustand.richtung=r.dataset.richtung;if(!zustand.alarm)zustand.schwelle=vorbelegen(zustand.richtung);ringIst=null;renderBlatt('[data-richtung="'+zustand.richtung+'"]');return}
 const k=e.target.closest('[data-kanal]');
 if(k){const n=k.dataset.kanal,an=!zustand[n];if(!an&&!zustand[n==='push'?'email':'push'])return;zustand[n]=an;renderBlatt('[data-kanal="'+n+'"]');return}
 const a=e.target.closest('[data-alarm]');if(!a)return;
 const was=a.dataset.alarm;
 if(was==='zu')zu();
 else if(was==='speichern')speichern(a);
 else if(was==='loeschen'){zustand.frage=true;renderBlatt('[data-alarm="loeschen-ja"]')}
 else if(was==='loeschen-nein'){zustand.frage=false;renderBlatt('[data-alarm="loeschen"]')}
 else if(was==='loeschen-ja'){a.disabled=true;try{daten=await api('alarme/'+zustand.alarm.id,{method:'DELETE'});melden();zu()}catch{zustand.fehler=at('fehler');renderBlatt()}}
 else if(was==='push-an'){a.disabled=true;try{typeof pushEinschalten==='function'&&await pushEinschalten()}catch{}zu()}
 else if(was==='neu'){oeffneBlatt(null,oeffner)}
 else if(was==='mitteilungen'){zu();IT.oeffneMitteilungen&&IT.oeffneMitteilungen(oeffner)}
 else if(was.startsWith('bearbeiten:')){const al=liste().find(x=>String(x.id)===was.slice(11));if(al)oeffneBlatt(al,oeffner)}
});
blatt.addEventListener('toggle',()=>{},true);

/* ---------- Liste "Deine Alarme" ---------- */
function oeffneListe(von){
 oeffner=von||document.activeElement;
 const w=wert(),l=liste(),ab=a=>Math.abs(a.schwelle-(w??a.schwelle));
 const zeile=a=>{const off=a.zustand==='bereit';
  return '<li><button type="button" class="liste-zeile" data-alarm="bearbeiten:'+a.id+'"><span class="liste-ring'+(off?'':' grau')+'" aria-hidden="true"></span><span class="liste-text">'+esc(at(a.richtung==='ueber'?'zeileUeber':'zeileUnter').replace('{x}',a.schwelle))+'</span>'
   +'<span class="liste-rest">'+esc(a.zustand==='pausiert'?at('pausiert'):w==null?'':ab(a)===0?at('genauKurz'):at('nochKurz').replace('{n}',ab(a)))+'</span>'+SVG.pfeil+'</button></li>'};
 const gruppe=(r,titel,sym)=>{const g=l.filter(a=>a.richtung===r&&a.zustand!=='ausgeloest').sort((x,y)=>ab(x)-ab(y));
  return g.length?'<h3 class="liste-gruppe">'+sym+'<span>'+esc(at(titel))+'</span></h3><ul class="liste">'+g.map(zeile).join('')+'</ul>':''};
 const aus=l.filter(a=>a.zustand==='ausgeloest');
 const ausHtml=aus.length?'<details class="liste-aus"><summary><span class="liste-ring grau" aria-hidden="true"></span><span>'+esc(at('ausgeloestN').replace('{n}',aus.length))+'</span>'+SVG.runter+'</summary><ul class="liste">'
  +aus.map(a=>'<li><button type="button" class="liste-zeile aus" data-alarm="bearbeiten:'+a.id+'"><span class="liste-text"><b>'+esc(at(a.richtung==='ueber'?'zeileUeber':'zeileUnter').replace('{x}',a.schwelle))
   +(a.ausgeloest_am?' · '+esc(at('ausgeloestAm').replace('{d}',datumKurz(a.ausgeloest_am))):'')+'</b><small>'+esc(erklaerung(a))+'</small></span>'+SVG.pfeil+'</button></li>').join('')+'</ul></details>':'';
 const beideVoll=zaehl('ueber')>=JE&&zaehl('unter')>=JE;
 zeigen('<h2 id="alarm-blatt-titel" tabindex="-1">'+esc(at('liste'))+'</h2><p class="blatt-unter">'+esc(w!=null?at('jetztListe').replace('{w}',w):'')+'</p>'
  +gruppe('ueber','steigtGr',SVG.hoch)+gruppe('unter','faelltGr',SVG.runter)+ausHtml
  +(beideVoll?'<p class="blatt-klein mitte">'+esc(at('beideVoll'))+'</p>':'<button type="button" class="blatt-neu" data-alarm="neu">'+esc(at('neu'))+'</button>')
  +'<button type="button" class="text-button blatt-mitteilungen" data-alarm="mitteilungen">'+esc(at('mitteilungen'))+'</button>');
}
function erklaerung(a){
 if(!a.ausgeloest_am)return at(a.richtung==='ueber'?'erklUeberNeu':'erklUnterNeu').replace('{x}',a.schwelle);
 return at(a.richtung==='ueber'?'erklUeber':'erklUnter').replace('{d}.','{d}').replace('{d}',datumKurz(a.ausgeloest_am).replace(/\.?$/,'.')).replace('{x}',a.schwelle);
}
IT.alarmErklaerung=erklaerung;

/* ---------- Marken am Bogen (hoechstens zwei, nur bereite Alarme) ---------- */
let schild=null;
function marken(){
 const svg=$('.gauge-svg'),stage=$('.gauge-stage');if(!svg||!stage)return;
 svg.querySelectorAll('.alarm-marke').forEach(x=>x.remove());stage.querySelectorAll('.alarm-marke-knopf').forEach(x=>x.remove());schildZu();
 if(!angemeldet()||wert()==null||svg.viewBox.baseVal.width!==500)return;
 const n=naechste(),w=wert(),breite=svg.getBoundingClientRect().width||430,s=500/breite,punkt=svg.querySelector('.gauge-point');
 [n.ueber,n.unter].filter(Boolean).forEach(a=>{
  const ang=(180+a.schwelle*1.8)*Math.PI/180,x=250+200*Math.cos(ang),y=250+200*Math.sin(ang);
  const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('class','alarm-marke');c.setAttribute('cx',x.toFixed(1));c.setAttribute('cy',y.toFixed(1));
  c.setAttribute('r',(4*s).toFixed(2));c.style.strokeWidth=(2*s).toFixed(2)+'px';
  /* nah am Wertpunkt (< 3 Punkte): Wertpunkt bleibt obenauf */
  if(punkt&&Math.abs(a.schwelle-w)<3)svg.insertBefore(c,punkt);else svg.append(c);
  const b=document.createElement('button');b.type='button';b.className='alarm-marke-knopf';b.dataset.marke=a.id;
  b.setAttribute('aria-label',at('markeAria').replace('{r}',at(a.richtung==='ueber'?'ueber':'unter')).replace('{x}',a.schwelle));
  stage.append(b);b._marke=c;
 });
 knopfLage();
}
/* Klickflaeche genau ueber der gezeichneten Marke (unabhaengig vom Seitenverhaeltnis der Buehne) */
function knopfLage(){const st=$('.gauge-stage');if(!st)return;const sr=st.getBoundingClientRect();
 st.querySelectorAll('.alarm-marke-knopf').forEach(b=>{const r=b._marke&&b._marke.getBoundingClientRect();if(!r)return;b.style.left=(r.left+r.width/2-sr.left)+'px';b.style.top=(r.top+r.height/2-sr.top)+'px'})}
function schildZu(){if(schild){schild.remove();schild=null}}
function schildAuf(knopf){
 const a=liste().find(x=>String(x.id)===knopf.dataset.marke),w=wert();if(!a||w==null)return;
 if(schild&&schild.dataset.marke===knopf.dataset.marke){schildZu();return}
 schildZu();schild=document.createElement('span');schild.className='alarm-schild';schild.dataset.marke=a.id;schild.setAttribute('role','status');
 const rest=Math.abs(a.schwelle-w);schild.textContent=rest?at('schild').replace('{r}',at(a.richtung==='ueber'?'ueber':'unter')).replace('{x}',a.schwelle).replace('{n}',rest):at(a.richtung==='ueber'?'ueber':'unter')+' '+a.schwelle+' · '+at('genauKurz');
 document.body.append(schild);
 /* ausserhalb des Bogens: vom Mittelpunkt weg nach aussen versetzt, nie ueber der grossen Zahl, nie abgeschnitten */
 const st=$('.gauge-stage').getBoundingClientRect(),kr=knopf.getBoundingClientRect(),mx=st.left+st.width/2,my=st.top+st.height*(250/300);
 const cx=kr.left+kr.width/2,cy=kr.top+kr.height/2,dx=cx-mx,dy=cy-my,l=Math.hypot(dx,dy)||1,sw=schild.offsetWidth,sh=schild.offsetHeight;
 let x=cx+dx/l*24-(dx<0?sw:0),y=cy+dy/l*24-sh/2+scrollY;if(Math.abs(dx)<sw/2)x=cx-sw/2;
 x=Math.max(8,Math.min(innerWidth-sw-8,x));schild.style.left=x+'px';schild.style.top=Math.max(scrollY+4,y)+'px';
}
document.addEventListener('click',e=>{
 const m=e.target.closest('.alarm-marke-knopf');if(m){e.preventDefault();schildAuf(m);return}
 if(schild&&!e.target.closest('.alarm-schild'))schildZu();
 const a=e.target.closest('#alarm-karte [data-alarm]');if(!a)return;e.preventDefault();
 if(a.dataset.alarm==='login'){try{sessionStorage.setItem('investtimer-nach-login','alarm')}catch{}$('#account-login')?.click();return}
 if(IT.premiumSperre){IT.oeffneKonto&&IT.oeffneKonto(a,'paywall');return}  /* Alarme gehoeren zu Premium (Nachtrag N2) */
 if(a.dataset.alarm==='neu')oeffneBlatt(null,a);else oeffneListe(a);
});
addEventListener('resize',()=>{marken()});

/* ---------- Oeffentliche Schnittstelle, Aktualisierung ---------- */
IT.alarmNeu=von=>{laden().then(()=>oeffneBlatt(null,von))};
IT.alarmListe=von=>{laden().then(()=>oeffneListe(von))};
IT.alarmBearbeiten=(id,von)=>{laden().then(()=>{const a=liste().find(x=>String(x.id)===String(id));if(a)oeffneBlatt(a,von);else oeffneListe(von)})};
IT.alarmNeuLaden=()=>laden(true);
IT.oeffneAlarme=von=>IT.alarmListe(von);
function nachLogin(){let ziel=null;try{ziel=sessionStorage.getItem('investtimer-nach-login');if(ziel)sessionStorage.removeItem('investtimer-nach-login')}catch{}
 if(ziel==='alarm'&&angemeldet()){document.querySelectorAll('dialog.access-dialog[open]').forEach(d=>d.close());laden(true).then(()=>oeffneBlatt(null,$('#alarm-karte button')))}}
document.addEventListener('investtimer:update',()=>{if(!angemeldet()){daten=null;karte();marken();return}laden(!daten).then(()=>{karte();marken();nachLogin()})});
document.addEventListener('investtimer:wertfertig',()=>{setTimeout(marken,matchMedia('(prefers-reduced-motion: reduce)').matches?0:900)});
new MutationObserver(()=>{karte();if(blatt.open&&zustand&&blatt.querySelector('.blatt-segment'))renderBlatt();marken()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
karte();if(angemeldet())laden().then(()=>{karte();marken()});
})();
