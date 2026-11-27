/* Aufbau des Werts (Auftrag 25.11.2026, Block K): Karte auf der Startseite (ersetzt "Mehr erfahren"), Reiter #aufbau mit den drei
   Blickwinkeln und ihren Bestandteilen, Erklaerungs-Blatt je Bestandteil. Ausgeloggt: schlanke Hinweiszeile zum Zeitversatz auf allen
   Reitern, Label ueber dem Bogen mit Datum. Gesamtwert, Teilwerte und Datum immer aus demselben Stand (IT.view: eingeloggt live,
   ausgeloggt der zeitversetzte publicSnapshot). Keine Gewichtungen, keine Rohwerte, keine Anzahl Bestandteile. */
(()=>{
const KEYS=['volatility','price','positioning'];
const AT={de:{
  karteKopf:'DAS STECKT IN DER {w}',karteKopfAus:'DAS STECKTE IN DER {w}',details:'Details',karteAus:'Stand {d} · live nach Anmeldung',
  volatility:'Kursschwankungen',price:'Breite und Trend',positioning:'Stimmung und Absicherung',
  eyebrow:'AUFBAU DES MARKTSTRESS',titel:'Drei Blickwinkel. Ein Wert.',
  intro:'Wie nervös ist der Markt, wie breit ist die Schwäche und wie vorsichtig sind die Anleger? Diese drei Perspektiven ergänzen sich.',
  gesamt:'Marktstress heute, aus allen drei Blickwinkeln',gesamtAus:'Marktstress am {d}',
  frage:{volatility:'Wie viel Unsicherheit preist der Markt ein?',price:'Wie viele Aktien tragen die Entwicklung?',positioning:'Wie vorsichtig verhalten sich Anleger?'},
  text:{volatility:'Erwartete Schwankungen und die Verteilung der Unsicherheit über verschiedene Zeiträume.',price:'Die Lage einzelner Aktien und der langfristige Trend des Gesamtmarkts.',positioning:'Absicherung, Marktstimmung und Unruhe am Anleihemarkt.'},
  einfluss:'Was einfließt ({n})',fuss:'Jeder Blickwinkel steht auf einer Skala von 0 bis 100. Keine Anlageberatung.',verlauf:'Blickwinkel im Verlauf ansehen',
  was:'Was wird betrachtet?',stress:'Was bedeutet mehr Stress?',warum:'Warum gehört das dazu?',schliessen:'Schließen',ohneTeil:'Teilwerte für diesen Stand nicht verfügbar',
  stufen:['ruhig','moderat','erhöht','hoch','Panik'],
  hinweis:'Stand {d} · einen Monat zeitversetzt.',hinweis2:'Angemeldet siehst du alles live.',anmelden:'Anmelden',
  hinweis2Premium:'Mit Premium siehst du alles live.',premium:'Premium ansehen',karteSperre:'Stand {d} · live mit Premium',
  labelAm:'MARKTSTRESS AM {d}',tab:'Aufbau'},
 en:{
  karteKopf:'WHAT MAKES UP THE {w}',karteKopfAus:'WHAT MADE UP THE {w}',details:'Details',karteAus:'As of {d} · live after sign-in',
  volatility:'Price fluctuations',price:'Breadth and trend',positioning:'Sentiment and protection',
  eyebrow:'HOW MARKET STRESS IS BUILT',titel:'Three perspectives. One score.',
  intro:'How nervous is the market, how widespread is weakness, and how cautious are investors? These three perspectives complement each other.',
  gesamt:'Market stress today, from all three perspectives',gesamtAus:'Market stress on {d}',
  frage:{volatility:'How much uncertainty is being priced in?',price:'How many stocks share in the market’s direction?',positioning:'How cautiously are investors behaving?'},
  text:{volatility:'Expected price swings and how uncertainty is distributed over different time horizons.',price:'The condition of individual stocks and the longer-term trend of the overall market.',positioning:'Protection activity, investor sentiment and bond market uncertainty.'},
  einfluss:'What goes into it ({n})',fuss:'Each perspective sits on a scale from 0 to 100. Not investment advice.',verlauf:'See the perspectives over time',
  was:'What do we look at?',stress:'What does more stress mean?',warum:'Why include it?',schliessen:'Close',ohneTeil:'Sub-scores not available for this reading',
  stufen:['calm','moderate','elevated','high','panic'],
  hinweis:'Snapshot from {d} · one month delayed.',hinweis2:'Sign in to see everything live.',anmelden:'Sign in',
  hinweis2Premium:'See everything live with Premium.',premium:'See Premium',karteSperre:'As of {d} · live with Premium',
  labelAm:'MARKET STRESS ON {d}',tab:'Breakdown'}};
const en=()=>document.documentElement.lang==='en',at=k=>AT[en()?'en':'de'][k];
const angemeldet=()=>!!IT.member;  /* sofort bekannt (gespeicherte Sitzung), kein Layoutsprung beim Laden */
/* zeitversetzter Stand: ausgeloggt oder angemeldet ohne Premium bei Premium-Pflicht (Nachtrag N2) */
const sperre=()=>angemeldet()&&!!IT.premiumSperre,verzoegert=()=>!angemeldet()||sperre();
const stand=()=>IT.view||{};
const runde=x=>Math.floor(x+0.5);
const datum=d=>d?new Date(Date.parse(d+'T12:00:00Z')).toLocaleDateString(en()?'en-US':'de-DE',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}):'';
const datumKurz=d=>d?new Date(Date.parse(d+'T12:00:00Z')).toLocaleDateString(en()?'en-US':'de-DE',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}):'';
const teil=k=>{const b=stand().bloecke||{};return Number.isFinite(b[k])?runde(b[k]):null};
const stufenwort=w=>w==null?'':at('stufen')[ITStufe.stufe(w)]||'';
const erkl=()=>window.ITErklaerungen||[];
const PFEIL='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m8 5 5 5-5 5"/></svg>';
const UHR='<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="7.2"/><path d="M10 6v4.3l2.8 1.7"/></svg>';
const balken=(w,h)=>'<span class="aufbau-spur" style="height:'+h+'px"><span style="width:'+(w??0)+'%;background:'+(w==null?'transparent':ITStufe.farbe(w))+'"></span></span>';

/* ---------- Karte auf der Startseite ---------- */
const karte=document.createElement('a');karte.id='aufbau-karte';karte.className='aufbau-karte';karte.href='#aufbau';
(()=>{const as=$('.assessment');if(as)as.after(karte)})();
function karteZeichnen(){
 /* ohne Wert (Sitzung laedt noch): gleiche Hoehe mit Platzhaltern, unsichtbar ueber body.wert-laedt -> kein Layoutsprung */
 const v=stand(),w=v.rounded??'–';
 const aus=verzoegert(),hat=v.rounded==null||KEYS.some(k=>teil(k)!=null);
 karte.setAttribute('aria-label',(aus?at('karteKopfAus'):at('karteKopf')).replace('{w}',w)+' – '+at('details'));
 karte.innerHTML='<span class="aufbau-karte-kopf"><span class="aufbau-label">'+esc((aus?at('karteKopfAus'):at('karteKopf')).replace('{w}',w))+'</span><span class="aufbau-details">'+esc(at('details'))+PFEIL+'</span></span>'
  +(hat?KEYS.map(k=>{const x=teil(k);return '<span class="aufbau-zeile"><span class="aufbau-name">'+esc(at(k))+'</span><span class="aufbau-wert">'+(x??'–')+'</span>'+balken(x,4)+'</span>'}).join('')
   :'<span class="aufbau-ohne">'+esc(at('ohneTeil'))+'</span>')
  +(aus&&v.asOf?'<span class="aufbau-stand">'+UHR+'<span>'+esc(at(sperre()?'karteSperre':'karteAus').replace('{d}',datumKurz(v.asOf)))+'</span></span>':'');
}

/* ---------- Reiter Aufbau ---------- */
const panel=document.createElement('section');panel.id='aufbau-ansicht';panel.className='aufbau-ansicht';panel.hidden=true;panel.setAttribute('aria-labelledby','aufbau-titel');
($('#verlauf-ansicht')||$('.app-header')||document.body).after(panel);
const offen=new Set();
function panelZeichnen(fokus){
 const v=stand(),w=v.rounded,aus=verzoegert(),liste=erkl();
 const gruppen=KEYS.map(k=>{const x=teil(k),teile=liste.filter(e=>e.block===k),id='aufbau-teile-'+k,auf=offen.has(k);
  return '<article class="aufbau-gruppe"><div class="aufbau-gruppe-kopf"><h3>'+esc(at(k))+'</h3><span class="aufbau-gruppe-wert">'+(x??'–')
   +(x!=null?'<small>'+esc(stufenwort(x))+'</small>':'')+'</span></div>'+balken(x,5)
   +'<p class="aufbau-frage">'+esc(at('frage')[k])+'</p><p class="aufbau-text">'+esc(at('text')[k])+'</p>'
   +'<button type="button" class="aufbau-auf" aria-expanded="'+auf+'" aria-controls="'+id+'" data-gruppe="'+k+'">'+esc(at('einfluss').replace('{n}',teile.length))+'<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4"/></svg></button>'
   +'<ul class="aufbau-teile" id="'+id+'"'+(auf?'':' hidden')+'>'+teile.map(e=>{const c=e[en()?'en':'de'];
    return '<li><button type="button" data-erkl="'+esc(e.id)+'"><span><b>'+esc(c.title)+'</b><small>'+esc(c.kicker||'')+'</small></span>'+PFEIL+'</button></li>'}).join('')+'</ul></article>'}).join('');
 panel.innerHTML='<div class="aufbau-inhalt"><span class="eyebrow">'+esc(at('eyebrow'))+'</span><h2 id="aufbau-titel" tabindex="-1">'+esc(at('titel'))+'</h2><p class="aufbau-intro">'+esc(at('intro'))+'</p>'
  +'<div class="aufbau-gesamt"><span>'+esc(aus?at('gesamtAus').replace('{d}',datum(v.asOf)):at('gesamt'))+'</span><b style="color:'+ITStufe.text(w)+'">'+(w??'–')+'<small>'+esc(w!=null?at('stufen')[ITStufe.stufe(w)].replace(/^./,c=>c.toUpperCase()):'')+'</small></b></div>'
  +gruppen+'<p class="aufbau-fuss">'+esc(at('fuss'))+'</p><a class="aufbau-verlauf" href="#verlauf">'+esc(at('verlauf'))+PFEIL+'</a></div>';
 if(fokus)panel.querySelector(fokus)?.focus({preventScroll:true});
}
panel.addEventListener('click',e=>{
 const g=e.target.closest('[data-gruppe]');if(g){const k=g.dataset.gruppe;offen.has(k)?offen.delete(k):offen.add(k);panelZeichnen('[data-gruppe="'+k+'"]');return}
 const b=e.target.closest('[data-erkl]');if(b)blattAuf(b.dataset.erkl,b);
 if(e.target.closest('.aufbau-verlauf'))try{sessionStorage.setItem('investtimer-verlauf-teilwerte','1')}catch{}
});
IT.aufbauAnsicht={zeigen(){panel.hidden=false;panelZeichnen()},verbergen(){panel.hidden=true;blatt.open&&blatt.close()}};

/* ---------- Erklaerungs-Blatt (gleiche Optik wie das Alarm-Blatt) ---------- */
const blatt=document.createElement('dialog');blatt.className='alarm-blatt aufbau-blatt';blatt.setAttribute('aria-labelledby','aufbau-blatt-titel');document.body.append(blatt);
let blattVon=null;
function blattAuf(id,von){
 const e=erkl().find(x=>x.id===id);if(!e)return;const c=e[en()?'en':'de'];blattVon=von;
 blatt.innerHTML='<div class="blatt-griff" aria-hidden="true"></div><button type="button" class="blatt-zu" aria-label="'+esc(at('schliessen'))+'"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5 5 15"/></svg></button>'
  +'<span class="aufbau-label">'+esc(at(e.block))+'</span><h2 id="aufbau-blatt-titel" tabindex="-1">'+esc(c.title)+'</h2><p class="blatt-unter">'+esc(c.kicker||'')+'</p>'
  +'<h3>'+esc(at('was'))+'</h3><p>'+esc(c.what)+'</p><h3>'+esc(at('stress'))+'</h3><p>'+esc(c.stress)+'</p><h3>'+esc(at('warum'))+'</h3><p>'+esc(c.why)+'</p>';
 blatt.showModal();$('#aufbau-blatt-titel').focus({preventScroll:true});
}
blatt.addEventListener('click',e=>{if(e.target.closest('.blatt-zu')){blatt.close();return}
 if(e.target===blatt){const r=blatt.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)blatt.close()}});
blatt.addEventListener('close',()=>{blattVon&&blattVon.isConnected&&blattVon.focus({preventScroll:true})});

/* ---------- Ausgeloggt: Hinweiszeile zum Zeitversatz (alle Reiter), Label ueber dem Bogen ---------- */
const zeile=$('#zeitversatz-zeile')||(()=>{const z=document.createElement('div');z.className='zeitversatz-zeile';z.hidden=true;z.setAttribute('role','note');return z})();
($('.app-header')||document.body).after(zeile);
/* Label ueber dem Bogen: eigenes Element neben dem h1 (das h1 wird bei jedem render() aus den Texten neu gesetzt) */
const h1=$('#score-title'),label=document.createElement('span');label.className='label-am';label.setAttribute('aria-hidden','true');if(h1)h1.after(label);
function ausgeloggtZeichnen(){
 const kopf=$('.app-header');if(kopf&&kopf.nextElementSibling!==zeile)kopf.after(zeile);  /* immer direkt unter der Kopfzeile, auch wenn Ansichten spaeter eingefuegt werden */
 const echtAus=!angemeldet(),sp=sperre(),aus=echtAus||sp,p=IT.pub||{};
 document.body.classList.toggle('it-ausgeloggt',echtAus);
 /* ausgeloggt sofort Platz reservieren (unsichtbar bis das Datum da ist): kein Layoutsprung beim Laden */
 zeile.hidden=!aus;zeile.classList.toggle('wartet-auf-daten',aus&&!p.asOf);zeile.classList.toggle('zz-premium',sp);
 if(aus){const html=UHR+'<p><b>'+esc(at('hinweis').replace('{d}',p.asOf?datumKurz(p.asOf):datumKurz('2026-10-27')))+'</b> <span>'+esc(at(sp?'hinweis2Premium':'hinweis2'))+'</span> <button type="button" class="'+(sp?'zeitversatz-premium':'zeitversatz-anmelden')+'">'+esc(at(sp?'premium':'anmelden'))+'</button></p>';
  if(zeile.innerHTML!==html)zeile.innerHTML=html}
 const am=aus&&p.asOf?at('labelAm').replace('{d}',datumKurz(p.asOf).toUpperCase()):'';label.textContent=am;
 if(h1){h1.classList.toggle('mit-datum',!!am);if(am)h1.setAttribute('aria-label',am);else h1.removeAttribute('aria-label')}
}
zeile.addEventListener('click',e=>{const pr=e.target.closest('.zeitversatz-premium');if(pr){IT.oeffneKonto&&IT.oeffneKonto(pr,'paywall');return}
 if(e.target.closest('.zeitversatz-anmelden')){try{sessionStorage.setItem('investtimer-nach-login','start')}catch{}$('#account-login')?.click()}});

/* Reihenfolge unter dem Einordnungssatz (I3): Aufbau-Karte, Film-Karte (nur ausgeloggt), Alarm, KI */
function ordnen(){const as=$('.assessment');if(!as)return;['#aufbau-karte','#film-karte','#alarm-karte','.ki-bruecke-start'].map(x=>$(x)).filter(Boolean).reduce((v,el)=>{if(v.nextElementSibling!==el)v.after(el);return el},as)}
function alles(){ordnen();karteZeichnen();ausgeloggtZeichnen();if(!panel.hidden)panelZeichnen()}
document.addEventListener('investtimer:update',alles);
addEventListener('hashchange',()=>requestAnimationFrame(ausgeloggtZeichnen));
document.addEventListener('investtimer:wertfertig',alles);
new MutationObserver(alles).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
alles();
})();
