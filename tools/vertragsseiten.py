#!/usr/bin/env python3
"""Baut die Seiten fuer Kuendigung (§ 312k BGB) und Widerruf (§ 356a BGB) nach public/.

Die Seiten sind ohne Anmeldung erreichbar. Verlinkt werden sie im Fuss der Hauptseite
erst, wenn deploy/abo.json "vertragsseiten": true enthaelt (zum Start der Abos).
Die API nimmt Erklaerungen nur mit IT_PAYWALL=1 an.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KOPF = (ROOT / "docs" / "rechtstexte" / "_kopf.html").read_text(encoding="utf-8")
FUSS = (ROOT / "docs" / "rechtstexte" / "_fuss.html").read_text(encoding="utf-8")
CSP_ALT = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'"
CSP_NEU = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'"

STIL = """<style>
form{display:grid;gap:14px;margin-top:20px}
label{font-weight:600;font-size:15px}
input,select,textarea{accent-color:var(--accent);font:inherit;font-size:16px;width:100%;min-height:48px;padding:10px 12px;border:1px solid #b8c4bd;border-radius:10px;background:#fff;color:var(--text)}
textarea{min-height:110px}
fieldset{border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:0;display:grid;gap:8px}
legend{font-weight:600;font-size:15px;padding:0 4px}
.wahl{display:flex;gap:10px;align-items:center;font-weight:400;min-height:44px}.wahl input{width:22px;min-height:22px;height:22px;margin:0}
.knopf{min-height:52px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-weight:600;font-size:17px;font-family:inherit;cursor:pointer;padding:0 18px}
.knopf.leise{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.fehler{color:#b3261e;font-size:14px;min-height:1em;margin:0}
.bestaetigung{border:2px solid var(--accent);border-radius:12px;padding:16px 18px;margin-top:20px}
.bestaetigung dl{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;margin:10px 0}.bestaetigung dt{color:var(--sub)}.bestaetigung dd{margin:0}
@media print{.zurueck,footer,.knopf{display:none}}
</style>"""

SKRIPT = """<script>
(function(){
 const f=document.getElementById('erklaerung'),fehler=document.getElementById('fehler'),aus=document.getElementById('ergebnis');
 const T={name:'Bitte gib deinen Namen an.',email:'Bitte gib eine gültige E-Mail-Adresse an.',grund:'Bitte nenne den Grund für die außerordentliche Kündigung.',
  datum:'Bitte wähle ein Datum.',inaktiv:'Diese Funktion ist gerade nicht verfügbar. Schreib uns bitte an info@investtimer.net.',limit:'Zu viele Versuche. Bitte versuche es morgen noch einmal oder schreib an info@investtimer.net.'};
 const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 function sichtbar(){const a=f.querySelector('[name=kuendigungsart]:checked'),g=document.getElementById('grund-feld'),z=f.querySelector('[name=zeitpunkt]:checked'),d=document.getElementById('datum-feld');
  if(g)g.hidden=!(a&&a.value==='ausserordentlich');if(d)d.hidden=!(z&&z.value==='datum')}
 f.addEventListener('change',sichtbar);sichtbar();
 f.addEventListener('submit',async e=>{e.preventDefault();fehler.textContent='';const k=f.querySelector('button[type=submit]');k.disabled=true;
  const daten=Object.fromEntries(new FormData(f).entries());
  if(!daten.name||daten.name.trim().length<2){fehler.textContent=T.name;k.disabled=false;f.name.focus();return}
  if(!/^[^@\\s]+@[^@\\s]+\\.[a-z]{2,}$/i.test(daten.email||'')){fehler.textContent=T.email;k.disabled=false;f.email.focus();return}
  try{const r=await fetch(f.dataset.ziel,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(daten)});const d=await r.json().catch(()=>({}));
   if(!r.ok)throw d.error||'fehler';
   const a=d.angaben||{},z=[['Eingang',d.eingang+' (Nr. '+d.nummer+')'],['Name',d.name],['E-Mail',d.email],['Vertrag',a.vertrag]];
   if(d.art==='kuendigung'){z.push(['Art',a.kuendigungsart==='ordentlich'?'ordentliche Kündigung':'außerordentliche Kündigung']);if(a.grund)z.push(['Grund',a.grund]);
    z.push(['Zeitpunkt',a.zeitpunkt==='datum'?'zum '+a.datum:'zum nächstmöglichen Zeitpunkt']);if(d.ende)z.push(['Vertragsende',d.ende])}
   else if(a.bestelldatum)z.push(['Bestellt am',a.bestelldatum]);
   aus.innerHTML='<div class="bestaetigung" role="status" tabindex="-1"><h2>'+(d.art==='kuendigung'?'Deine Kündigung ist eingegangen.':'Dein Widerruf ist eingegangen.')+'</h2><dl>'
    +z.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl><p>Eine Bestätigung mit diesen Angaben schicken wir dir per E-Mail an '+esc(d.email)+'.'
    +(d.art==='kuendigung'&&!d.ende?' Das Vertragsende bestätigen wir dir, sobald wir die Kündigung bearbeitet haben.':'')+'</p>'
    +'<button type="button" class="knopf leise" onclick="window.print()">Bestätigung drucken oder als PDF speichern</button></div>';
   f.hidden=true;aus.firstChild.focus();
  }catch(x){fehler.textContent=T[x]||'Das hat nicht geklappt. Bitte versuche es noch einmal oder schreib an info@investtimer.net.';k.disabled=false}
 });
})();
</script>"""

KUENDIGEN = """<h1>Verträge hier kündigen</h1>
<p>Hier kündigst du dein Abo „InvestTimer Premium“ – ohne Anmeldung. Nach dem Klick auf „Jetzt kündigen“ siehst du sofort eine Bestätigung, die du speichern kannst, und bekommst sie zusätzlich per E-Mail.</p>
<p class="klein">Abos, die du in der iOS-App über Apple abgeschlossen hast, kündigst du in den Einstellungen deiner Apple-ID (Einstellungen → dein Name → Abonnements). Du kannst sie trotzdem hier melden; wir erklären dir dann den Weg.</p>
<form id="erklaerung" data-ziel="/api/vertrag/kuendigen" novalidate>
<fieldset><legend>Art der Kündigung</legend>
<label class="wahl"><input type="radio" name="kuendigungsart" value="ordentlich" checked> Ordentliche Kündigung</label>
<label class="wahl"><input type="radio" name="kuendigungsart" value="ausserordentlich"> Außerordentliche Kündigung (aus wichtigem Grund)</label></fieldset>
<div id="grund-feld" hidden><label for="grund">Grund der außerordentlichen Kündigung</label><textarea id="grund" name="grund" maxlength="2000"></textarea></div>
<fieldset><legend>Zeitpunkt</legend>
<label class="wahl"><input type="radio" name="zeitpunkt" value="naechstmoeglich" checked> Zum nächstmöglichen Zeitpunkt</label>
<label class="wahl"><input type="radio" name="zeitpunkt" value="datum"> Zu einem bestimmten Datum</label></fieldset>
<div id="datum-feld" hidden><label for="datum">Datum</label><input id="datum" name="datum" type="date"></div>
<label for="name">Vor- und Nachname</label><input id="name" name="name" autocomplete="name" required maxlength="120">
<label for="email">E-Mail-Adresse deines InvestTimer-Kontos</label><input id="email" name="email" type="email" autocomplete="email" required maxlength="254">
<p class="klein">Vertrag: InvestTimer Premium (monatlich oder jährlich). An diese Adresse schicken wir die Bestätigung.</p>
<p class="fehler" id="fehler" role="alert"></p>
<button class="knopf" type="submit">Jetzt kündigen</button>
</form>
<div id="ergebnis"></div>"""

WIDERRUFEN = """<h1>Vertrag widerrufen</h1>
<p>Hier widerrufst du deinen Vertrag über „InvestTimer Premium“ – ohne Anmeldung. Nach dem Klick auf „Widerruf bestätigen“ siehst du sofort eine Eingangsbestätigung und bekommst sie zusätzlich per E-Mail.</p>
<p class="klein">Käufe in der iOS-App wickelt Apple ab. Dafür gilt das Verfahren von Apple (reportaproblem.apple.com).</p>
<form id="erklaerung" data-ziel="/api/vertrag/widerrufen" novalidate>
<label for="name">Vor- und Nachname</label><input id="name" name="name" autocomplete="name" required maxlength="120">
<label for="email">E-Mail-Adresse deines InvestTimer-Kontos</label><input id="email" name="email" type="email" autocomplete="email" required maxlength="254">
<label for="bestelldatum">Bestellt am (wenn bekannt)</label><input id="bestelldatum" name="bestelldatum" type="date">
<p class="klein">Vertrag: InvestTimer Premium (monatlich oder jährlich).</p>
<p class="fehler" id="fehler" role="alert"></p>
<button class="knopf" type="submit">Widerruf bestätigen</button>
</form>
<div id="ergebnis"></div>"""


def main():
    kopf = KOPF.replace(CSP_ALT, CSP_NEU).replace("</style>", "</style>\n<meta name=\"robots\" content=\"noindex\">")
    assert CSP_NEU in kopf
    for datei, titel, inhalt in (("vertrag-kuendigen.html", "Verträge hier kündigen", KUENDIGEN),
                                 ("vertrag-widerrufen.html", "Vertrag widerrufen", WIDERRUFEN)):
        (ROOT / "public" / datei).write_text(kopf.replace("__TITEL__", titel).replace("</head>", STIL + "</head>")
                                             + inhalt + SKRIPT + FUSS, encoding="utf-8")
        print("geschrieben:", datei)


if __name__ == "__main__":
    main()
