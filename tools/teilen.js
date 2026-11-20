/* Teilen (Auftrag C, 20.11.2026): Knopf auf der Startseite (Wert), im Verlauf (gewaehlter Zeitraum) und in jeder Ereigniskarte (Phase).
   Bilder vorab gerendert (server/teilen_bilder.py), standardmaessig zeitversetzter Stand (7-Tage-Regel), auch eingeloggt.
   Mobil mit navigator.share + Datei: natives Teilen-Menue mit Bild 1080x1350, Text und Link.
   Sonst eigener Dialog: Bild, Bild herunterladen, Link kopieren, WhatsApp, LinkedIn, X, Threads (nur einfache Teilen-Adressen,
   keine Skripte der Netzwerke). Links /s/... tragen utm_source=teilen&utm_medium=<kanal>; gezaehlt wird cookiefrei ueber /api/v. */
(()=>{
const TT={de:{teilen:'Teilen',ariaWert:'Wert teilen',ariaVerlauf:'Verlauf teilen',ariaPhase:'Phase teilen',
  band:'Geteilt: Marktstress {w} ({s}) · Stand {d}',bandKnopf:'Kostenlos registrieren & aktuellen Wert sehen',bandZu:'Hinweis schließen',titel:'Teilen',bildAlt:'Bild zum Teilen',laden:'Bild herunterladen',hoch:'Hochformat',
  kopieren:'Link kopieren',kopiert:'Link kopiert',schliessen:'Schließen',stand:'Stand {d}',fehlt:'Das Bild ist gerade nicht verfügbar.',
  wert:'Marktstress am US-Aktienmarkt: {w} von 100 ({s}) · Stand {d}',vl:'Marktstress {z} · Stand {d}',ph:'{n}: höchster Marktstress {w} am {d}.',
  stufen:['Ruhig','Moderat','Erhöht','Hoch','Panik'],spannen:{'1M':'im letzten Monat','3M':'in den letzten 3 Monaten','1J':'in den letzten 12 Monaten','5J':'in den letzten 5 Jahren','A':'seit 2006'}},
 en:{teilen:'Share',ariaWert:'Share score',ariaVerlauf:'Share history',ariaPhase:'Share phase',
  band:'Shared: market stress {w} ({s}) · as of {d}',bandKnopf:'Sign up free & see today’s score',bandZu:'Close notice',titel:'Share',bildAlt:'Image to share',laden:'Download image',hoch:'Portrait',
  kopieren:'Copy link',kopiert:'Link copied',schliessen:'Close',stand:'As of {d}',fehlt:'The image isn’t available right now.',
  wert:'Market stress in the US stock market: {w} out of 100 ({s}) · as of {d}',vl:'Market stress {z} · as of {d}',ph:'{n}: highest market stress {w} on {d}.',
  stufen:['Calm','Moderate','Elevated','High','Panic'],spannen:{'1M':'over the past month','3M':'over the past 3 months','1J':'over the past 12 months','5J':'over the past 5 years','A':'since 2006'}}};
const en=()=>document.documentElement.lang==='en',sp=()=>en()?'en':'de',tt=k=>TT[sp()][k];
const SYM='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 15V4M8 8l4-4 4 4"/><path d="M6 11H5v9h14v-9h-1"/></svg>';
const datum=d=>new Date(Date.parse(d+'T12:00:00Z')).toLocaleDateString(en()?'en-US':'de-DE',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
const stufe=w=>[20,40,60,80].filter(g=>w>=g).length;
/* Stand mit Uhrzeit (Live-Stand, Europe/Berlin) oder nur Datum (zeitversetzter Tagesstand) */
const standText=(m,tag)=>{if(m.zeit&&!tag){const z=new Date(m.zeit);const t=z.toLocaleString(en()?'en-US':'de-DE',{timeZone:'Europe/Berlin',day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});return t}return datum(tag||m.asOf)};
let manifest=null,laedt=null;
function ladeManifest(){if(manifest)return Promise.resolve(manifest);if(laedt)return laedt;
 laedt=fetch('/teilen/aktuell/manifest.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).then(m=>{manifest=m;laedt=null;return m}).catch(()=>{laedt=null;return null});return laedt}
function zaehlen(a){try{IT.zaehlen&&IT.zaehlen(a)}catch{}}

/* Knopf als HTML (Verlauf und Ereigniskarte bauen ihn in ihr Markup ein) */
function knopf(art,phase){const aria=art==='verlauf'?tt('ariaVerlauf'):art==='phase'?tt('ariaPhase'):tt('ariaWert');
 return '<button type="button" class="teilen-knopf" data-teilen="'+art+'"'+(phase?' data-phase="'+esc(phase)+'"':'')+' aria-label="'+esc(aria)+'">'+SYM+'<span aria-hidden="true">'+esc(tt('teilen'))+'</span></button>'}
IT.teilenKnopf=knopf;

/* Startseite: in der Stufen-Zeile (Platz liegt fest im HTML, kein Layoutsprung) */
function startKnopf(){const k=$('.teilen-start');if(k)k.innerHTML=knopf('wert')}

/* Was wird geteilt: Bildname, Link, Text */
function ziel(m,art,phase){
 if(!m)return null;const z=IT.verlaufZeitraum?IT.verlaufZeitraum():'1J',st=m.stamp||m.asOf;
 if(art==='verlauf')return {name:'verlauf-'+z,pfad:'/s/verlauf/'+z+'/'+st,text:tt('vl').replace('{z}',tt('spannen')[z]).replace('{d}',standText(m,m.stamp?null:(m.spannen||{})[z]))};
 if(art==='phase'){const p=(m.phasen||{})[phase];if(!p)return null;
  return {name:'phase-'+phase,pfad:'/s/phase/'+phase,text:tt('ph').replace('{n}',en()?p.name_en:p.name).replace('{w}',p.spitze.w).replace('{d}',datum(p.spitze.d))}}
 return {name:'wert',pfad:'/s/wert/'+st,text:tt('wert').replace('{w}',m.wert).replace('{s}',tt('stufen')[stufe(m.wert)]).replace('{d}',standText(m))};
}
/* Eingeloggt (Schalter IT_TEILEN_AKTUELL an): aktueller Stand aus /api/teilen/stand (gleiche Quelle wie /api/aktuell);
   der Server rendert die Bilder je Wert und Zeitstempel einmal und legt sie oeffentlich ab, damit die Link-Vorschau genau
   dieses Bild zeigt. Ausgeloggt: zeitversetzter Stand (was der Besucher sieht). */
async function stand(){
 if(IT.member&&IT.session){try{const tok=IT.token?await IT.token():null;const r=await fetch('/api/teilen/stand',{cache:'no-store',headers:tok?{Authorization:'Bearer '+tok}:{}});
  if(r.ok){const m=await r.json();if(m.aktuell)return m}}catch{}}
 return ladeManifest();
}
async function bildUrl(m,z,fmt){
 const datei=z.name+'-'+fmt+'-'+sp()+'.png';
 if(!m.stamp)return '/teilen/'+m.asOf+'/'+datei;
 const q=z.name.split('-'),art=q[0],tok=IT.token?await IT.token():null;
 const r=await fetch('/api/teilen/bild?aktuell=1&art='+art+(art==='verlauf'?'&zeitraum='+q[1]:'')+(art==='phase'?'&phase='+q[1]:'')+'&format='+fmt+'&l='+sp(),
  {headers:tok?{Authorization:'Bearer '+tok}:{}});
 if(!r.ok)throw 0;return new URL(r.url).pathname}
const link=(z,kanal)=>location.origin+z.pfad+'?'+(en()?'l=en&':'')+'utm_source=teilen&utm_medium='+kanal;

async function teilen(art,phase,quelle){
 const m0=await stand();let m=m0,z=ziel(m,art,phase);
 if(!z&&m0&&m0.stamp){m=await ladeManifest();z=ziel(m,art,phase)}   /* Phase nur im zeitversetzten Stand: dann von dort */
 if(!z){typeof toast==='function'&&toast(tt('fehlt'));return}
 const nativ=navigator.share&&navigator.canShare&&matchMedia('(pointer:coarse)').matches;
 try{z.hoch=await bildUrl(m,z,'hoch');if(!nativ)z.quer=await bildUrl(m,z,'quer')}catch{typeof toast==='function'&&toast(tt('fehlt'));return}
 zaehlen('teilen-'+art);
 if(nativ){
  try{const r=await fetch(z.hoch);if(!r.ok)throw 0;const b=await r.blob();
   const f=new File([b],'investtimer-'+z.name+'.png',{type:'image/png'}),url=link(z,'nativ');
   if(navigator.canShare({files:[f]})){await navigator.share({files:[f],title:'InvestTimer',text:z.text+' '+url});zaehlen('teilen-'+art+'-nativ');return}
  }catch(e){if(e&&e.name==='AbortError')return}
 }
 dialog(art,z,quelle);
}

let dlg=null,zurueck=null;
function dialog(art,z,quelle){
 zurueck=quelle||document.activeElement;
 if(!dlg){dlg=document.createElement('dialog');dlg.className='teilen-dialog';dlg.setAttribute('aria-labelledby','teilen-titel');document.body.append(dlg);
  dlg.addEventListener('close',()=>{zurueck&&zurueck.focus&&zurueck.focus({preventScroll:true})});
  dlg.addEventListener('click',e=>{if(e.target===dlg){dlg.close();return}
   const b=e.target.closest('[data-kanal]');if(b)zaehlen('teilen-'+dlg.dataset.art+'-'+b.dataset.kanal);
   if(e.target.closest('[data-teilen-zu]'))dlg.close();
   const k=e.target.closest('[data-kopieren]');if(k){const u=k.dataset.kopieren;
    (navigator.clipboard?navigator.clipboard.writeText(u):Promise.reject()).catch(()=>{const i=document.createElement('textarea');i.value=u;document.body.append(i);i.select();try{document.execCommand('copy')}catch{}i.remove()})
     .finally(()=>{const s=k.querySelector('span');s.textContent=tt('kopiert');setTimeout(()=>{if(s.isConnected)s.textContent=tt('kopieren')},2200)})}})}
 dlg.dataset.art=art;
 if(!z.quer)z.quer=z.hoch;
 const enc=encodeURIComponent,quer=z.quer,hoch=z.hoch;
 const netz=[['whatsapp','WhatsApp','https://wa.me/?text='+enc(z.text+' '+link(z,'whatsapp'))],
  ['linkedin','LinkedIn','https://www.linkedin.com/sharing/share-offsite/?url='+enc(link(z,'linkedin'))],
  ['x','X','https://x.com/intent/post?text='+enc(z.text)+'&url='+enc(link(z,'x'))],
  ['threads','Threads','https://www.threads.net/intent/post?text='+enc(z.text+' '+link(z,'threads'))]];
 dlg.innerHTML='<div class="teilen-kopf"><h2 id="teilen-titel">'+esc(tt('titel'))+'</h2><button type="button" class="teilen-zu" data-teilen-zu aria-label="'+esc(tt('schliessen'))+'">×</button></div>'
  +'<img class="teilen-bild" src="'+quer+'" width="1200" height="630" alt="'+esc(tt('bildAlt'))+': '+esc(z.text)+'">'
  +'<p class="teilen-text">'+esc(z.text)+'</p>'
  +'<div class="teilen-aktionen"><a class="teilen-aktion primaer" data-kanal="download" href="'+quer+'" download="investtimer-'+esc(z.name)+'.png">'+esc(tt('laden'))+'</a>'
  +'<a class="teilen-aktion" data-kanal="download-hoch" href="'+hoch+'" download="investtimer-'+esc(z.name)+'-hoch.png">'+esc(tt('hoch'))+'</a>'
  +'<button type="button" class="teilen-aktion" data-kanal="link" data-kopieren="'+esc(link(z,'link'))+'"><span>'+esc(tt('kopieren'))+'</span></button></div>'
  +'<div class="teilen-netze">'+netz.map(([k,n,u])=>'<a class="teilen-netz" data-kanal="'+k+'" href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+n+'</a>').join('')+'</div>';
 const img=dlg.querySelector('.teilen-bild');img.addEventListener('error',()=>{img.replaceWith(Object.assign(document.createElement('p'),{className:'teilen-text',textContent:tt('fehlt')}))},{once:true});
 if(!dlg.open)dlg.showModal();dlg.querySelector('.teilen-zu').focus({preventScroll:true});
}

document.addEventListener('click',e=>{const b=e.target.closest('[data-teilen]');if(!b)return;e.preventDefault();e.stopPropagation();teilen(b.dataset.teilen,b.dataset.phase,b)},true);

/* Ankunft ueber einen geteilten Link: Sprache, Besuch zaehlen (ohne Kennung), Parameter aus der Adresse entfernen */
(()=>{const q=new URLSearchParams(location.search);
 if(q.get('lang')==='en'&&document.documentElement.lang!=='en'){const h=$('#header-language');if(h){h.value='en';h.dispatchEvent(new Event('change',{bubbles:true}))}}
 if(q.get('utm_source')==='teilen'){const m=(q.get('utm_medium')||'link').replace(/[^a-z0-9-]/g,'').slice(0,20)||'link';setTimeout(()=>zaehlen('besuch-teilen-'+m),400)}
 if(q.get('geteilt')&&/^[0-9T-]{10,15}$/.test(q.get('st')||''))IT.teilenBand={art:q.get('geteilt'),st:q.get('st')};
 if(['utm_source','utm_medium','lang','z','phase','geteilt','st'].some(k=>q.has(k))){IT.teilenStart={z:q.get('z'),phase:q.get('phase')};
  ['utm_source','utm_medium','utm_campaign','lang','z','phase','geteilt','st'].forEach(k=>q.delete(k));
  try{history.replaceState(history.state,'',location.pathname+(q.toString()?'?'+q:'')+location.hash)}catch{}}})();

/* Band fuer Besucher eines geteilten Links (nur ausgeloggt): geteilter Wert mit Stand, Registrieren, schliessbar */
async function band(){
 const b=IT.teilenBand;if(!b||IT.member){$('.geteilt-band')?.remove();return}
 let m=null;try{const r=await fetch('/teilen/'+(b.st.includes('T')?'live/':'')+b.st+'/manifest.json',{cache:'no-cache'});m=r.ok?await r.json():null}catch{}
 if(!m||m.wert==null)return;
 let el=$('.geteilt-band');if(!el){el=document.createElement('div');el.className='geteilt-band';el.setAttribute('role','note');($('.score-column')||document.body).prepend(el)}
 el.innerHTML='<span>'+esc(tt('band').replace('{w}',m.wert).replace('{s}',tt('stufen')[stufe(m.wert)]).replace('{d}',standText(m)))+'</span>'
  +'<button type="button" class="primary" data-band-registrieren>'+esc(tt('bandKnopf'))+'</button>'
  +'<button type="button" class="geteilt-zu" data-band-zu aria-label="'+esc(tt('bandZu'))+'">×</button>';
}
document.addEventListener('click',e=>{
 if(e.target.closest('[data-band-zu]')){IT.teilenBand=null;$('.geteilt-band')?.remove();return}
 if(e.target.closest('[data-band-registrieren]')){IT.zugangModus&&IT.zugangModus('registrieren');$('#account-login')?.click();setTimeout(()=>{IT.zugangModus&&IT.zugangModus('registrieren');IT.zugangNeu&&IT.zugangNeu()},0)}
});
startKnopf();band();
document.addEventListener('investtimer:update',()=>{startKnopf();band()});
new MutationObserver(()=>{startKnopf();if($('.geteilt-band'))band()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
ladeManifest();
})();
