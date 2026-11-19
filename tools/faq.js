/* Haeufige Fragen als eigene Ansicht (#faq). Akkordeon: eine Frage offen, Tastatur (Pfeile, Pos1/Ende, Enter/Leertaste).
   Texte im Stil der KI-Antworten (du-Form, keine Kuerzel, keine Gewichte, keine Datenquellen, keine Empfehlungen).
   Abo-Fragen nur mit Paywall-Schalter (Build: __FAQ_ABO__). FAQPage-Strukturdaten erzeugt der Build aus derselben Liste. */
(()=>{
const FAQ=__FAQ__;
const FT={de:{eyebrow:'HÄUFIGE FRAGEN',titel:'Gut zu wissen',unter:'Kurze Antworten auf das, was am häufigsten gefragt wird.'},
 en:{eyebrow:'FAQ',titel:'Good to know',unter:'Short answers to the questions we hear most.'}};
const ft=k=>FT[document.documentElement.lang==='en'?'en':'de'][k];
let offen=0;
const sicht=document.createElement('section');sicht.id='faq-ansicht';sicht.className='faq-ansicht';sicht.hidden=true;sicht.setAttribute('aria-labelledby','faq-titel');
($('#feedback-ansicht')||$('.app-header'))?.after(sicht);
function zeichne(){
 const l=document.documentElement.lang==='en'?'en':'de';
 sicht.innerHTML='<div class="faq-kopf"><span class="eyebrow faq-eyebrow">'+ft('eyebrow')+'</span><h2 id="faq-titel" tabindex="-1">'+esc(ft('titel'))+'</h2><p class="faq-unter">'+esc(ft('unter'))+'</p></div>'
  +'<div class="faq-liste">'+FAQ.map((f,i)=>{const auf=i===offen;
   return '<div class="faq-eintrag'+(auf?' offen':'')+'"><h3 class="faq-frage-h"><button type="button" class="faq-frage" id="faq-f'+i+'" aria-expanded="'+auf+'" aria-controls="faq-a'+i+'" data-faq="'+i+'">'
    +'<span>'+esc(f[l].f)+'</span><svg class="faq-pfeil" viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button></h3>'
    +'<div class="faq-antwort" id="faq-a'+i+'" role="region" aria-labelledby="faq-f'+i+'"'+(auf?'':' hidden')+'><p>'+f[l].a+'</p></div></div>'}).join('')+'</div>';
}
sicht.addEventListener('click',e=>{const b=e.target.closest('[data-faq]');if(!b)return;const i=Number(b.dataset.faq);offen=offen===i?-1:i;zeichne();$('#faq-f'+i)?.focus({preventScroll:true})});
sicht.addEventListener('keydown',e=>{const b=e.target.closest('[data-faq]');if(!b)return;const i=Number(b.dataset.faq),n=FAQ.length;let z=null;
 if(e.key==='ArrowDown')z=(i+1)%n;else if(e.key==='ArrowUp')z=(i-1+n)%n;else if(e.key==='Home')z=0;else if(e.key==='End')z=n-1;if(z==null)return;e.preventDefault();$('#faq-f'+z)?.focus()});
IT.faqAnsicht={zeigen(){const war=sicht.hidden;sicht.hidden=false;if(war)zeichne()},verbergen(){sicht.hidden=true}};
new MutationObserver(()=>{if(!sicht.hidden)zeichne()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
})();
