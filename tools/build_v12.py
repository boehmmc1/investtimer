#!/usr/bin/env python3
"""Baut die Seite aus dem UI-Export v1.2 (oeffentliche Ansicht + Ansicht nach Login).

Aufruf: build_v12.py <export_v1.2.html> <zielordner> [--vorschau]

Der Export bestimmt Aufbau, Texte und Gestaltung. Ergaenzt wird nur, was ihn
an den Betrieb anschliesst:
  - Rohwerte, Anker und Rechenkern entfernt (laufen in der Volafly-API)
  - zwei Staende aus /data/stress.json: oeffentlich (zeitversetzt) und aktuell
  - KI-Dialog spricht mit /api/chat statt Beispielantworten zu zeigen
  - Film als eigene Datei statt 3,7 MB im HTML
  - "Weitere Fragen" im KI-Dialog aus volafly-api/investtimer_fragen.json

--vorschau: Seite bekommt noindex. Der Ansichtswechsel "Oeffentlich / Nach Login"
bleibt in jedem Fall, bis es eine echte Anmeldung gibt.

--anmeldung=<datei>: echte Anmeldung per E-Mail-Link (Supabase-Projekt von
InvestTimer; Datei mit {"url": ..., "anonKey": ...}, beides oeffentlich). Dann
  - oeffentlich nur der zeitversetzte Stand, der aktuelle Wert kommt mit
    Login-Token ueber /api/aktuell, die KI verlangt das Token ebenfalls
  - der Entwurfs-Umschalter "Oeffentlich / Nach Login" entfaellt

Immer: Halbmond-Fuellung des Signalbogens, Halbmond als Zeichen der KI und als
Denk-Anzeige, Web-App-Manifest.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "volafly-api"))
sys.path.insert(0, str(ROOT / "tools"))
import marktstress as engine  # noqa: E402
from build_public import GAUGE_CSS, GAUGE_JS, MOBILE_CSS, once, sub_once  # noqa: E402

# Halbmond: Zeichen der KI (gefuellt bis zum angezeigten Wert) und Denk-Anzeige
MOND = ('<svg class="{cls}" viewBox="3 13 42 24" aria-hidden="true">'
        '<path class="mond-spur" d="M6 34a18 18 0 0 1 36 0" pathLength="100"/>'
        '<path class="mond-wert" d="M6 34a18 18 0 0 1 36 0" pathLength="100"/></svg>')

HALBMOND_CSS = """
/* Halbmond als Zeichen der KI und als Denk-Anzeige */
.ki-halbmond{overflow:visible}
.ki-halbmond path{fill:none;stroke-width:4.2;stroke-linecap:round}
.ki-halbmond .mond-spur{stroke:#d3dccf}
.ki-halbmond .mond-wert{stroke:var(--accent);stroke-dasharray:var(--value,0) 100;transition:stroke-dasharray .9s cubic-bezier(.16,1,.3,1)}
.chat-wait .ki-halbmond{width:24px;height:14px;flex:none}
.chat-wait .ki-halbmond .mond-wert{stroke-dasharray:22 100;transition:none;animation:ki-denkt 1.5s cubic-bezier(.65,0,.35,1) infinite alternate}
@keyframes ki-denkt{from{stroke-dashoffset:0}to{stroke-dashoffset:-78}}
@media(prefers-reduced-motion:reduce){.chat-wait .ki-halbmond .mond-wert{animation:none;stroke-dasharray:var(--value,0) 100}.ki-halbmond .mond-wert{transition:none}}
"""

ANMELDUNG_CSS = """
.zugang-reiter{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:4px;margin:4px 0 16px;border-radius:12px;background:var(--panel)}
.zugang-reiter button{min-height:44px;border-radius:9px;font-size:15px;color:var(--sub)}
.zugang-reiter button[aria-selected=true]{background:var(--surface,#fff);color:var(--text);font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.pw-feld{position:relative;display:flex;min-width:0}.pw-feld input{flex:1;min-width:0;width:100%;box-sizing:border-box;padding-right:96px!important}
.pw-zeigen{position:absolute;right:4px;top:50%;transform:translateY(-50%);min-height:40px;min-width:44px;padding:0 10px;font-size:13px;color:var(--accent);border-radius:8px}
.pw-hinweis{font-size:12px;color:var(--sub);margin:4px 0 0;line-height:1.5}
.konto-pw{margin-top:18px;border-top:1px solid var(--line);padding-top:12px;font-size:14px}
.konto-pw summary{cursor:pointer;min-height:44px;display:flex;align-items:center;color:var(--sub)}
.konto-pw form{display:grid;gap:6px;margin-top:6px}.konto-pw input{width:100%;box-sizing:border-box;min-height:44px;font-size:16px;border-radius:10px;border:1px solid var(--line);padding:0 12px;background:transparent;color:var(--text)}
.konto-pw .ok{color:var(--accent)}
/* Anmeldung per E-Mail-Link */
.access-form{display:grid;gap:8px;margin:20px 0 4px;text-align:left}
.access-form label{font-size:12px;color:var(--sub)}
.access-form input{min-height:48px;font-size:16px;padding:0 14px;border:1px solid #b9c7b6;border-radius:12px;background:var(--surface);color:var(--text);font-family:inherit}
.access-form input:focus{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}
.access-form button:disabled{opacity:.55}
.access-error{min-height:1.2em;margin:0;font-size:12px;line-height:1.5;color:#9b3d32}
.access-error.ok{color:var(--accent)}
.access-form .code-input{font-size:24px;letter-spacing:.42em;text-align:center;font-variant-numeric:tabular-nums;padding-left:.42em}
.access-form .code-input::placeholder{color:#c9d3c6}
.access-form button[type=submit]{min-height:48px}
.access-more{display:flex;justify-content:space-between;gap:12px;margin:14px 0 0}
.text-button{min-height:44px;padding:0 4px;border:0;background:none;color:var(--accent);font:inherit;font-size:13px;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.text-button:disabled{color:var(--sub);text-decoration:none;cursor:default}
.access-dialog{overscroll-behavior:contain}
.access-dialog .preview-notice a{color:inherit}
@media(max-width:760px){.access-dialog{max-height:calc(100dvh - 12px);overflow-y:auto}.access-benefits{margin-bottom:4px}}
.rechtliches{font-size:12px;color:var(--sub)}.rechtliches a{color:inherit;display:inline-block;padding:12px 2px}
/* Alarme, Push, Installation */
#saved-alerts{display:none}
/* Angemeldet: Einstieg zu den Alarmen direkt unter dem Wert (im Entwurf nur tief in den Details) */
.members-layout .score-column .subscribe-module{display:block;margin-top:18px}
.alarm-erklaerung{font-size:13px;line-height:1.55;color:var(--text);margin:8px 0 2px;min-height:2.6em}
.alarm-kanal{border:1px solid var(--line);border-radius:12px;padding:8px 12px;margin:10px 0 4px;display:grid;gap:2px}.alarm-kanal legend{font-size:13px;color:var(--sub);padding:0 4px}.alarm-kanal .wahl{display:flex;gap:10px;align-items:center;min-height:40px;font-size:15px}.alarm-kanal input{accent-color:var(--accent);width:20px;height:20px;margin:0}.alarm-mailhinweis{font-size:12px;color:var(--sub);margin:4px 0 0;line-height:1.5;overflow-wrap:anywhere}.alarm-kanal-wahl{min-height:40px;font-size:14px;border:1px solid var(--line);border-radius:8px;background:transparent;color:var(--text);padding:0 6px;flex:1;min-width:0;max-width:200px}
.alarm-eintrag .alarm-text{flex:1 1 100%}
.push-test-status{font-size:13px;line-height:1.55;margin-top:6px}.push-test-status:empty{display:none}.push-test-status.ok b{color:var(--accent)}.push-test-status.fehler,.push-test-status.warnung b{color:#b3261e}.push-test-status ul{margin:6px 0 0;padding-left:18px}.push-test-status li{margin:4px 0}.push-test-status summary{cursor:pointer;min-height:36px;display:flex;align-items:center;color:var(--sub)}
.push-box{margin:18px 0;padding:14px 16px;border:1px solid var(--line);border-radius:14px;background:var(--panel);font-size:14px;line-height:1.6}
.push-box p{margin:0 0 8px;color:var(--text)}.push-box p:last-child{margin-bottom:0}.push-box .primary{margin-top:6px}.push-box .access-more{margin:4px 0 0}
.alarm-liste{list-style:none;margin:6px 0 14px;padding:0;display:grid;gap:8px}
.alarm-eintrag{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.alarm-eintrag.pausiert .alarm-text{opacity:.6}
.alarm-text{flex:1;display:grid;gap:2px}.alarm-text b{font-size:15px;font-weight:500}.alarm-text small{font-size:12px;color:var(--sub)}
.alarm-schalter{position:relative;display:inline-flex;align-items:center;min-height:44px;flex:none;cursor:pointer}
.alarm-schalter input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:pointer}
.alarm-schalter .spur{position:relative;display:block;width:46px;height:28px;border-radius:14px;background:#cfd8cc;transition:background .2s}
.alarm-schalter .spur::after{content:"";position:absolute;top:3px;left:3px;width:22px;height:22px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.2);transition:transform .2s}
.alarm-schalter input:checked+.spur{background:var(--accent)}.alarm-schalter input:checked+.spur::after{transform:translateX(18px)}
.alarm-schalter input:focus-visible+.spur{outline:2px solid var(--accent);outline-offset:2px}
.alarm-leer{font-size:14px;color:var(--sub);margin:6px 0 14px}
.alarm-form select{min-height:48px;font-size:16px;padding:0 12px;border:1px solid #b9c7b6;border-radius:12px;background:var(--surface);color:var(--text);font-family:inherit}
.alarm-schwelle{display:flex;justify-content:space-between;align-items:baseline;margin-top:8px}
.alarm-schwelle output{font-size:28px;font-variant-numeric:tabular-nums;color:var(--text)}
.alarm-form input[type=range]{width:100%;min-height:44px;accent-color:var(--accent)}
.install-schritte{margin:8px 0 0;padding-left:22px;display:grid;gap:8px;font-size:14px;line-height:1.55}
.install-schritte .teilen{width:18px;height:18px;vertical-align:-3px;color:var(--accent)}
.install-link{font-size:12px;color:var(--sub);min-height:44px}
@media(prefers-reduced-motion:reduce){.alarm-schalter .spur,.alarm-schalter .spur::after{transition:none}}
/* Ohne Impressum und Datenschutzerklaerung: kein Einstieg in Registrierung oder Anmeldung */
body.ohne-registrierung:not(.members-layout) #open-subscribe,
body.ohne-registrierung:not(.members-layout) .public-access-note,
body.ohne-registrierung:not(.members-layout) #account-login,
body.ohne-registrierung:not(.members-layout) .benefit-line{display:none}
"""

TEXTE_KONTO_DE = ("kontoMenueLabel:'Kontomenü',kontoMenueKonto:'Mein Konto',kontoMenueAlarme:'Meine Alarme',kontoMenueAbo:'Abo verwalten',"
                  "pwAendernTitel:'Passwort ändern',pwAlt:'Aktuelles Passwort',pwAendernKnopf:'Passwort ändern',"
                  "pwOhneAlt:'Noch kein Passwort oder vergessen? Code per E-Mail',pwCodeText:'Wir haben dir einen Bestätigungscode geschickt. Gib ihn ein und wähle dein neues Passwort.',"
                  "pwCodeGesendet:'Code ist unterwegs.',pwAltFalsch:'Das aktuelle Passwort stimmt nicht.',pwGeaendert:'Dein Passwort ist geändert.',"
                  "kontoLink:'Mein Konto',premiumFreischalten:'Premium freischalten',kontoEyebrow:'DEIN KONTO',kontoTitel:'Mein Konto',kontoAngemeldet:'Angemeldet als {email}',kontoAboTitel:'Abonnement',"
                  "kontoFreiTitel:'Kostenloser Zugang',kontoFreiOffen:'Aktueller Wert, KI-Fragen und Alarme sind mit deiner Anmeldung derzeit freigeschaltet.',"
                  "kontoFrei:'Du siehst den zeitversetzten Wert. Aktueller Wert, ganze Historie, KI-Analysen und Alarme gehören zu Premium.',"
                  "kontoAbgelaufen:'Premium endete am',premiumAnsehen:'Premium ansehen',"
                  "st_test:'Testphase',st_aktiv:'aktiv',st_gekuendigt:'gekündigt',st_zahlungsproblem:'Zahlung offen',st_abgelaufen:'abgelaufen',st_erstattet:'erstattet',st_frei:'kostenlos',"
                  "kontoPreis:'Preis',kontoKanal:'Bezahlt über',kontoBeginn:'Beginn',kontoNaechste:'Nächste Verlängerung',kontoEnde:'Premium bis',"
                  "kontoAuto:'Automatische Verlängerung',kontoTestRest:'Verbleibende Testtage',an:'an',aus:'aus',jahr:'Jahr',monat:'Monat',"
                  "kanalWeb:'Website (Stripe)',kanalPromo:'Freischaltung',"
                  "kontoZahlungsproblem:'Die letzte Zahlung hat nicht geklappt. Bitte prüfe deine Zahlungsmethode, sonst endet Premium.',"
                  "aboVerwalten:'Abo verwalten oder kündigen',aboVerwaltenWeb:'Dort kündigst du, wechselst den Tarif, änderst die Zahlungsmethode und lädst Rechnungen.',"
                  "aboVerwaltenApple:'Dein Abo läuft über Apple. Kündigen und Tarif wechseln geht in den Abo-Einstellungen deiner Apple-ID.',"
                  "aboVerwaltenGoogle:'Dein Abo läuft über Google Play. Kündigen und Tarif wechseln geht im Play Store.',"
                  "aboVerwaltenWebInApp:'Dein Abo hast du auf der Website abgeschlossen. Verwalten und kündigen kannst du es auf investtimer.net unter „Mein Konto“.',"
                  "kontoKi:'KI-Fragen heute: {n} von {max}',"
                  "loeschenTitel:'Konto löschen',loeschenText:'Damit löschst du dein Konto, deine Alarme (auch E-Mail-Alarme) und Push-Geräte endgültig. Rechnungen und Zahlungsbelege bewahren Apple bzw. Stripe nach den gesetzlichen Fristen auf.',"
                  "loeschenEingabe:'Zur Bestätigung „löschen“ eingeben',loeschenKnopf:'Konto endgültig löschen',loeschenWort:'Bitte gib „löschen“ ein.',"
                  "loeschenAbo:'Dein Abo verlängert sich noch automatisch. Kündige es zuerst unter „Abo verwalten“, dann kannst du das Konto löschen.',"
                  "geloeschtTitel:'Dein Konto ist gelöscht.',geloeschtText:'Alle Daten zu deinem Konto sind entfernt. Den zeitversetzten Wert siehst du weiter ohne Anmeldung.',"
                  "paywallEyebrow:'INVESTTIMER PREMIUM',paywallTitel:'Marktstress aktuell, mit KI-Analyse.',"
                  "paywallIntro:'Premium schaltet alles frei, was über den zeitversetzten Wert hinausgeht:',"
                  "v1:'Aktueller Marktstress, alle 10 Minuten neu',v2:'Vollständige historische Entwicklung',v3:'Alle Einzelindikatoren im Detail',"
                  "v4:'KI-Analysen: Fragen zum aktuellen Stand, verständlich beantwortet',v5:'Eigene Schwellen mit Push-Mitteilung',"
                  "tarifWahl:'Tarif wählen',tarifJahr:'Jährlich',tarifMonat:'Monatlich',tarifSpar:'rund 33 % günstiger',tarifJahrSub:'entspricht 3,33 € im Monat',"
                  "tarifDanach:'{preis} pro {intervall}',tarifTest:'Die ersten 7 Tage sind kostenlos. Danach {danach}, erste Abbuchung am {datum}.',"
                  "tarifAuto:'Das Abo verlängert sich automatisch, bis du kündigst. Kündigen geht jederzeit, auch in der Testphase, ohne Kündigungsfrist zum Ende des laufenden Zeitraums.',"
                  "ctaTest:'7 Tage kostenlos testen',ctaAbo:'Premium abonnieren',wiederherstellen:'Käufe wiederherstellen',"
                  "paywallFuss:'Preise inkl. USt. Keine Anlageberatung.',agb:'Abo-Bedingungen',datenschutz:'Datenschutz',zurueck:'Zurück',"
                  "fehlerSchonPremium:'Du hast Premium bereits. Details siehst du unter „Mein Konto“.',fehlerAbbruch:'Der Kauf wurde abgebrochen.',"
                  "fehlerInaktiv:'Abos sind gerade nicht verfügbar.',")
TEXTE_KONTO_EN = ("kontoMenueLabel:'Account menu',kontoMenueKonto:'My account',kontoMenueAlarme:'My alerts',kontoMenueAbo:'Manage subscription',"
                  "pwAendernTitel:'Change password',pwAlt:'Current password',pwAendernKnopf:'Change password',"
                  "pwOhneAlt:'No password yet or forgotten? Get a code by email',pwCodeText:'We sent you a confirmation code. Enter it and choose your new password.',"
                  "pwCodeGesendet:'Code is on its way.',pwAltFalsch:'The current password is incorrect.',pwGeaendert:'Your password has been changed.',"
                  "kontoLink:'My account',premiumFreischalten:'Unlock Premium',kontoEyebrow:'YOUR ACCOUNT',kontoTitel:'My account',kontoAngemeldet:'Signed in as {email}',kontoAboTitel:'Subscription',"
                  "kontoFreiTitel:'Free access',kontoFreiOffen:'The latest reading, AI questions and alerts are currently included with your sign-in.',"
                  "kontoFrei:'You see the delayed reading. The latest reading, full history, AI analysis and alerts are part of Premium.',"
                  "kontoAbgelaufen:'Premium ended on',premiumAnsehen:'See Premium',"
                  "st_test:'trial',st_aktiv:'active',st_gekuendigt:'cancelled',st_zahlungsproblem:'payment due',st_abgelaufen:'expired',st_erstattet:'refunded',st_frei:'free',"
                  "kontoPreis:'Price',kontoKanal:'Paid via',kontoBeginn:'Started',kontoNaechste:'Next renewal',kontoEnde:'Premium until',"
                  "kontoAuto:'Auto-renewal',kontoTestRest:'Trial days left',an:'on',aus:'off',jahr:'year',monat:'month',"
                  "kanalWeb:'Website (Stripe)',kanalPromo:'Granted',"
                  "kontoZahlungsproblem:'The last payment failed. Please check your payment method, otherwise Premium ends.',"
                  "aboVerwalten:'Manage or cancel',aboVerwaltenWeb:'Cancel, switch plan, update your payment method and download invoices there.',"
                  "aboVerwaltenApple:'Your subscription runs through Apple. Cancel or switch in your Apple ID subscription settings.',"
                  "aboVerwaltenGoogle:'Your subscription runs through Google Play. Cancel or switch in the Play Store.',"
                  "aboVerwaltenWebInApp:'You subscribed on the website. Manage or cancel it on investtimer.net under „My account“.',"
                  "kontoKi:'AI questions today: {n} of {max}',"
                  "loeschenTitel:'Delete account',loeschenText:'This permanently deletes your account, alerts (including email alerts) and push devices. Apple or Stripe keep invoices and receipts as required by law.',"
                  "loeschenEingabe:'Type „löschen“ to confirm',loeschenKnopf:'Delete account permanently',loeschenWort:'Please type „löschen“.',"
                  "loeschenAbo:'Your subscription still renews automatically. Cancel it under „Manage“ first, then delete the account.',"
                  "geloeschtTitel:'Your account has been deleted.',geloeschtText:'All data linked to your account has been removed. The delayed reading stays available without sign-in.',"
                  "paywallEyebrow:'INVESTTIMER PREMIUM',paywallTitel:'Live market stress, with AI analysis.',"
                  "paywallIntro:'Premium unlocks everything beyond the delayed reading:',"
                  "v1:'Latest market stress, updated every 10 minutes',v2:'Full history',v3:'Every indicator in detail',"
                  "v4:'AI analysis: questions about the current reading, answered plainly',v5:'Your own thresholds with push notifications',"
                  "tarifWahl:'Choose a plan',tarifJahr:'Yearly',tarifMonat:'Monthly',tarifSpar:'about 33 % less',tarifJahrSub:'equals €3.33 a month',"
                  "tarifDanach:'{preis} per {intervall}',tarifTest:'The first 7 days are free. Then {danach}, first charge on {datum}.',"
                  "tarifAuto:'The subscription renews automatically until you cancel. You can cancel any time, also during the trial, effective at the end of the current period.',"
                  "ctaTest:'Try 7 days free',ctaAbo:'Subscribe to Premium',wiederherstellen:'Restore purchases',"
                  "paywallFuss:'Prices incl. VAT. Not investment advice.',agb:'Subscription terms',datenschutz:'Privacy',zurueck:'Back',"
                  "fehlerSchonPremium:'You already have Premium. See „My account“ for details.',fehlerAbbruch:'The purchase was cancelled.',"
                  "fehlerInaktiv:'Subscriptions are not available right now.',")
KONTO_JS = (ROOT / "tools" / "konto.js").read_text(encoding="utf-8") + "\n" + (ROOT / "tools" / "verlauf.js").read_text(encoding="utf-8") + "\n" + (ROOT / "tools" / "kontomenue.js").read_text(encoding="utf-8")
TEXTE_VERLAUF_DE = ("verlaufTitel:'Verlauf',verlaufAria:'Verlauf des Marktstress, {n} Tageswerte',verlaufSpanne:'Zeitraum',verlaufAlle:'Alle',"
                    "verlaufNote:'{n} Tageswerte, zwischen {min} und {max}. Aufgezeichnet seit {seit}, je ein Wert pro Tag.',"
                    "verlaufPremium:'Den vollständigen Verlauf siehst du mit Premium.',verlaufFehlt:'Der Verlauf ist gerade nicht verfügbar.',")
TEXTE_VERLAUF_EN = ("verlaufTitel:'History',verlaufAria:'Market stress history, {n} daily readings',verlaufSpanne:'Period',verlaufAlle:'All',"
                    "verlaufNote:'{n} daily readings, between {min} and {max}. Recorded since {seit}, one reading per day.',"
                    "verlaufPremium:'The full history is part of Premium.',verlaufFehlt:'The history is not available right now.',")
KONTO_CSS = """
.app-header .header-tools{position:relative}
.konto-knopf{display:inline-flex;align-items:center;gap:6px;border:1px solid #bfccbc;border-radius:6px;padding:0 10px 0 6px;min-height:44px;min-width:44px;color:var(--accent);background:transparent;cursor:pointer}
.konto-knopf:hover,.konto-knopf[aria-expanded=true]{background:var(--panel);filter:none}
.konto-kreis{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--accent);color:#fff;font:600 14px/1 var(--sans)}
.konto-pfeil{width:12px;height:12px;transition:transform .15s}.konto-knopf[aria-expanded=true] .konto-pfeil{transform:rotate(180deg)}
.konto-menue{position:absolute;right:0;top:calc(100% + 8px);z-index:60;width:max-content;min-width:220px;max-width:min(300px,calc(100vw - 32px));box-sizing:border-box;background:var(--surface,#fff);border:1px solid #bfccbc;border-radius:6px;box-shadow:0 10px 30px rgba(27,51,48,.12);padding:6px;display:grid}
.konto-menue[hidden]{display:none}
.konto-menue-mail{padding:10px 12px 9px;font-size:12px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-bottom:1px solid var(--line);margin-bottom:4px}
.konto-menue [role=menuitem]{display:flex;align-items:center;min-height:44px;padding:0 12px;border-radius:4px;font-size:14px;color:var(--text);text-align:left;width:100%;white-space:nowrap}
.konto-menue [role=menuitem]:hover,.konto-menue [role=menuitem]:focus{background:var(--panel);filter:none}
.konto-menue [role=menuitem]:focus-visible{outline:2px solid #698dbc;outline-offset:-2px}
.konto-menue-linie{height:1px;background:var(--line);margin:4px 0}
@media(max-width:760px){.konto-pfeil{display:none}.konto-knopf{padding:0 6px}}
.konto-daten{margin:10px 0 12px;display:grid;gap:6px}.konto-zeile{display:flex;justify-content:space-between;gap:12px;font-size:14px}
.konto-zeile dt{color:var(--sub)}.konto-zeile dd{margin:0;text-align:right;color:var(--text)}
.konto-status{display:inline-block;margin-left:6px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);font-size:12px;color:var(--sub)}
.konto-status.s-aktiv,.konto-status.s-test{color:var(--text)}.konto-status.s-zahlungsproblem{color:#c0392b;border-color:#c0392b}
.konto-ki{font-size:14px;color:var(--sub)}
.konto-mail{font-size:14px;color:var(--sub);margin:-4px 0 14px;overflow-wrap:anywhere}.konto-abschnitt{font-size:13px;font-weight:600;margin:0 0 6px;color:var(--text)}
.konto-loeschen{margin-top:18px;border-top:1px solid var(--line);padding-top:12px;font-size:14px}
.konto-loeschen summary{cursor:pointer;min-height:44px;display:flex;align-items:center;color:var(--sub)}
.konto-loeschen input{width:100%;box-sizing:border-box;min-height:44px;margin:6px 0;font-size:16px;border-radius:10px;border:1px solid var(--line);padding:0 12px;background:transparent;color:var(--text)}
.danger{min-height:48px;border-radius:999px;border:1px solid #c0392b;background:transparent;color:#c0392b;font-weight:600;cursor:pointer}.danger.full{width:100%}
a.primary.full{display:flex;align-items:center;justify-content:center;text-decoration:none;box-sizing:border-box}
.premium-vorteile{margin:8px 0 16px;padding-left:20px;line-height:1.7;font-size:15px}.premium-vorteile .ki{font-weight:600}
.tarife{display:grid;gap:10px;margin:0 0 12px}
.tarif{position:relative;display:grid;gap:2px;padding:14px 16px;border:1px solid var(--line);border-radius:14px;cursor:pointer;background:var(--panel)}
.tarif.gewaehlt{border:2px solid var(--text);padding:13px 15px}.tarif input{position:absolute;opacity:0;pointer-events:none}
.tarif:focus-within{outline:2px solid var(--text);outline-offset:2px}
.tarif-kopf{display:flex;align-items:center;justify-content:space-between;gap:8px}.tarif-preis{font-size:20px;font-weight:600}.tarif-preis small,.tarif-sub{font-size:13px;color:var(--sub);font-weight:400}
.tarif-badge{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--text);color:var(--bg,#fff)}
.tarif-bedingung{font-size:13px;line-height:1.55;color:var(--sub)}
@media (min-width:560px){.tarife{grid-template-columns:1fr 1fr}}
.verlauf{margin:0 0 40px}.verlauf h3{font-size:13px;font-weight:500;margin:0 0 14px}.verlauf-knoepfe{display:flex;gap:6px;margin:0 0 12px}.verlauf-spanne{min-height:36px;min-width:44px;padding:0 12px;border:1px solid var(--line);border-radius:999px;font-size:12px;color:var(--sub)}.verlauf-spanne.aktiv{background:var(--text);color:var(--bg);border-color:var(--text)}.verlauf .primary{margin-top:10px}
"""

# Alarme, Push und Installation (tools/alarme.js)
ALARM_JS = (ROOT / "tools" / "alarme.js").read_text(encoding="utf-8")
TEXTE_ALARM_DE = ("alarmEyebrow:'DEINE ALARME',alarmTitle:'Deine Schwelle. Dein Hinweis.',"
                  "alarmIntro:'Lege fest, bei welchem Marktstress du eine Nachricht aufs Handy bekommst.',"
                  "alarmWenn:'Benachrichtigen, wenn der Marktstress',alarmSteigt:'über die Schwelle steigt',alarmFaellt:'unter die Schwelle fällt',"
                  "alarmSchwelle:'Schwelle',alarmSpeichern:'Alarm speichern',alarmUeber:'Steigt über',alarmUnter:'Fällt unter',"
                  "alarmAktiv:'aktiv',alarmPausiert:'pausiert',alarmLoeschen:'Löschen',alarmKeine:'Noch kein Alarm angelegt.',"
                  "alarmLaedt:'Wird geladen …',alarmFehler:'Das hat nicht geklappt. Bitte versuche es gleich noch einmal.',"
                  "alarmDoppelt:'Diesen Alarm gibt es schon.',alarmMax:'Du kannst bis zu fünf Alarme anlegen.',"
                  "alarmRegel:'Ein Alarm meldet sich, wenn der Wert die Schwelle überquert, höchstens einmal am Tag. Der Hinweis beschreibt nur den Stand und ist keine Anlageberatung.',"
                  "alarmErklUeber:'Du bekommst eine Nachricht, sobald der Marktstress über {x} steigt (also ab {x1}).',"
                  "alarmErklUeberSchon:'Der Marktstress liegt mit {w} bereits über {x}. Du bekommst die erste Nachricht, wenn er unter {x} fällt und danach wieder darüber steigt.',"
                  "alarmErklUnter:'Du bekommst eine Nachricht, sobald der Marktstress unter {x} fällt (also ab {x1}).',"
                  "alarmErklUnterSchon:'Der Marktstress liegt mit {w} bereits unter {x}. Du bekommst die erste Nachricht, wenn er über {x} steigt und danach wieder darunter fällt.',"
                  "alarmWartetUeber:'wartet, bis der Wert wieder unter {x} fällt',alarmWartetUnter:'wartet, bis der Wert wieder über {x} steigt',"
                  "pushAktiv:'Push ist auf diesem Gerät eingeschaltet.',pushTest:'Testnachricht senden',pushTestGesendet:'Testnachricht ist unterwegs',"
                  "alarmKanal:'Benachrichtigung per',kanal_push:'Push',kanal_email:'E-Mail',kanal_beide:'Push und E-Mail',"
                  "alarmMailAn:'E-Mails gehen an deine Konto-Adresse {email}. Jede Mail hat einen Abmeldelink.',alarmMailFehlt:'Für E-Mail-Alarme fehlt die Adresse deines Kontos. Bitte melde dich neu an.',"
                  "pushTestWarten:'Bitte kurz warten, dann noch einmal versuchen.',pushAus:'Push ausschalten',"
                  "pushTestSendet:'Wird gesendet …',pushTestAngenommen:'Vom Push-Dienst angenommen. Warte auf dein Gerät …',"
                  "pushTestZugestellt:'Zugestellt: Dein Gerät hat die Testnachricht erhalten.',pushTestTrotzdem:'Trotzdem keine Mitteilung zu sehen?',"
                  "pushTestNicht:'Nicht angekommen?',pushTestNichtText:'Der Push-Dienst hat die Nachricht angenommen, dein Gerät hat sie aber nicht bestätigt. Meist liegt es an diesen Einstellungen:',"
                  "pushTestAbgemeldet:'Dieses Gerät ist beim Push-Dienst nicht mehr angemeldet. Schalte Push aus und wieder ein.',"
                  "pushTestKeinGeraet:'Für dein Konto ist kein Gerät angemeldet. Schalte Push aus und wieder ein.',"
                  "pushTestAbgelehnt:'Der Push-Dienst hat die Nachricht nicht angenommen. Bitte versuche es später noch einmal.',"
                  "pushHinweisOs:'Mitteilungen für deinen Browser im Betriebssystem erlauben: am Mac unter Systemeinstellungen → Mitteilungen → Chrome bzw. Safari, unter Windows unter Einstellungen → System → Benachrichtigungen, unter Android unter Einstellungen → Apps → Browser → Benachrichtigungen.',"
                  "pushHinweisFokus:'Fokus- oder „Nicht stören“-Modus ausschalten oder InvestTimer bzw. den Browser dort zulassen.',"
                  "pushHinweisIos:'iPhone und iPad: Mitteilungen kommen nur in der installierten Web-App an (vom Home-Bildschirm geöffnet), nicht in Safari.',"
                  "pushHinweisBrowser:'Am Computer muss der Browser geöffnet sein, damit Mitteilungen ankommen.',"
                  "pushAusText:'Damit dich ein Alarm erreicht, schalte Mitteilungen auf diesem Gerät ein.',pushAn:'Mitteilungen einschalten',"
                  "pushBlockiert:'Mitteilungen sind für InvestTimer blockiert. Erlaube sie in den Einstellungen deines Geräts oder Browsers, dann klappt es.',"
                  "pushNein:'Dieser Browser kann keine Mitteilungen empfangen. Nutze ein aktuelles Chrome, Edge, Firefox oder Safari.',"
                  "iosTitel:'Auf dem iPhone kommen Mitteilungen nur in der installierten App an:',"
                  "ios1:'Tippe in Safari unten auf Teilen {teilen}.',ios2:'Wähle „Zum Home-Bildschirm“ und tippe auf „Hinzufügen“.',"
                  "ios3:'Öffne InvestTimer vom Home-Bildschirm und melde dich dort mit dem Code aus der E-Mail an.',"
                  "installLink:'App installieren',installTitel:'InvestTimer als App',"
                  "installIOS:'Ohne App Store, in drei Schritten (iPhone und iPad ab iOS 16.4):',"
                  "installAndroid:'InvestTimer lässt sich direkt installieren und startet dann wie eine App.',installJetzt:'Jetzt installieren',"
                  "installAndere:'In Chrome oder Edge: Menü ⋮ öffnen und „App installieren“ oder „Zum Startbildschirm hinzufügen“ wählen. In Safari auf dem Mac: Ablage → „Zum Dock hinzufügen“.',"
                  "installPush:'In der App kannst du Alarme mit Push-Mitteilung einrichten.',")
TEXTE_ALARM_EN = ("alarmEyebrow:'YOUR ALERTS',alarmTitle:'Your threshold. Your alert.',"
                  "alarmIntro:'Choose at which market stress level you get a notification.',"
                  "alarmWenn:'Notify me when market stress',alarmSteigt:'rises above the threshold',alarmFaellt:'falls below the threshold',"
                  "alarmSchwelle:'Threshold',alarmSpeichern:'Save alert',alarmUeber:'Rises above',alarmUnter:'Falls below',"
                  "alarmAktiv:'active',alarmPausiert:'paused',alarmLoeschen:'Delete',alarmKeine:'No alerts yet.',"
                  "alarmLaedt:'Loading …',alarmFehler:'That did not work. Please try again in a moment.',"
                  "alarmDoppelt:'This alert already exists.',alarmMax:'You can create up to five alerts.',"
                  "alarmRegel:'An alert fires when the score crosses the threshold, at most once a day. It only describes the reading and is not investment advice.',"
                  "alarmErklUeber:'You will get a notification as soon as market stress rises above {x} (that is, from {x1}).',"
                  "alarmErklUeberSchon:'Market stress is already above {x} at {w}. You will get the first notification once it falls below {x} and then rises above it again.',"
                  "alarmErklUnter:'You will get a notification as soon as market stress falls below {x} (that is, from {x1}).',"
                  "alarmErklUnterSchon:'Market stress is already below {x} at {w}. You will get the first notification once it rises above {x} and then falls below it again.',"
                  "alarmWartetUeber:'waiting until the score falls below {x} again',alarmWartetUnter:'waiting until the score rises above {x} again',"
                  "pushAktiv:'Push is on for this device.',pushTest:'Send test notification',pushTestGesendet:'Test notification is on its way',"
                  "alarmKanal:'Notify me by',kanal_push:'Push',kanal_email:'Email',kanal_beide:'Push and email',"
                  "alarmMailAn:'Emails go to your account address {email}. Every email has an unsubscribe link.',alarmMailFehlt:'Your account email address is missing. Please sign in again.',"
                  "pushTestWarten:'Please wait a moment, then try again.',pushAus:'Turn off push',"
                  "pushTestSendet:'Sending …',pushTestAngenommen:'Accepted by the push service. Waiting for your device …',"
                  "pushTestZugestellt:'Delivered: your device received the test notification.',pushTestTrotzdem:'Still no notification visible?',"
                  "pushTestNicht:'Not arrived?',pushTestNichtText:'The push service accepted the message, but your device did not confirm it. Usually one of these settings is the cause:',"
                  "pushTestAbgemeldet:'This device is no longer registered with the push service. Turn push off and on again.',"
                  "pushTestKeinGeraet:'No device is registered for your account. Turn push off and on again.',"
                  "pushTestAbgelehnt:'The push service did not accept the message. Please try again later.',"
                  "pushHinweisOs:'Allow notifications for your browser in the operating system: on a Mac under System Settings → Notifications → Chrome or Safari, on Windows under Settings → System → Notifications, on Android under Settings → Apps → Browser → Notifications.',"
                  "pushHinweisFokus:'Turn off Focus or Do Not Disturb, or allow InvestTimer or your browser there.',"
                  "pushHinweisIos:'iPhone and iPad: notifications only arrive in the installed web app (opened from the home screen), not in Safari.',"
                  "pushHinweisBrowser:'On a computer the browser must be running for notifications to arrive.',"
                  "pushAusText:'Turn on notifications on this device so alerts can reach you.',pushAn:'Turn on notifications',"
                  "pushBlockiert:'Notifications are blocked for InvestTimer. Allow them in your device or browser settings.',"
                  "pushNein:'This browser cannot receive notifications. Use a current Chrome, Edge, Firefox or Safari.',"
                  "iosTitel:'On iPhone, notifications only arrive in the installed app:',"
                  "ios1:'In Safari, tap Share {teilen} at the bottom.',ios2:'Choose “Add to Home Screen” and tap “Add”.',"
                  "ios3:'Open InvestTimer from your Home Screen and sign in there with the code from the email.',"
                  "installLink:'Install app',installTitel:'InvestTimer as an app',"
                  "installIOS:'No App Store needed, three steps (iPhone and iPad with iOS 16.4 or later):',"
                  "installAndroid:'InvestTimer can be installed directly and then starts like an app.',installJetzt:'Install now',"
                  "installAndere:'In Chrome or Edge: open the menu ⋮ and choose “Install app” or “Add to Home screen”. In Safari on Mac: File → “Add to Dock”.',"
                  "installPush:'In the app you can set up alerts with push notifications.',")

TEXTE_ANMELDUNG_DE = ("email:'E-Mail-Adresse',emailPlaceholder:'name@beispiel.de',pw:'Passwort',pwNeu:'Passwort festlegen',"
                      "pwZeigen:'Passwort anzeigen',pwZeigenKurz:'Anzeigen',pwVerbergenKurz:'Verbergen',"
                      "pwRegel:'Mindestens 10 Zeichen. Am sichersten ist ein Satz, den nur du kennst.',pwLeer:'Bitte gib dein Passwort ein.',"
                      "pwFalsch:'E-Mail-Adresse oder Passwort stimmen nicht.',pwSchwach:'Dieses Passwort ist zu schwach. Bitte wähle ein längeres.',"
                      "pwGleich:'Das neue Passwort muss sich vom bisherigen unterscheiden.',"
                      "loginSubmit:'Anmelden',registerTab:'Registrieren',registerTitle:'Konto anlegen.',registerSubmit:'Konto anlegen',"
                      "confirmTitle:'Bestätige deine E-Mail-Adresse.',confirmText:'Wir haben dir an {email} einen sechsstelligen Code geschickt. Gib ihn hier ein, dann ist dein Konto fertig.',"
                      "confirmSubmit:'Bestätigen',notConfirmed:'Deine E-Mail-Adresse ist noch nicht bestätigt. Wir haben dir einen neuen Code geschickt.',"
                      "alreadyRegistered:'Schon registriert? Dann melde dich an oder setze dein Passwort zurück.',"
                      "forgotLink:'Passwort vergessen?',forgotTitle:'Passwort zurücksetzen.',forgotText:'Gib deine E-Mail-Adresse ein. Wir schicken dir einen Code, mit dem du ein neues Passwort festlegst.',"
                      "forgotSubmit:'Code senden',resetTitle:'Neues Passwort festlegen.',resetText:'Wir haben dir an {email} einen Code geschickt, falls es dazu ein Konto gibt. Gib ihn ein und wähle ein neues Passwort.',"
                      "newPwText:'Wähle ein neues Passwort für dein Konto.',resetSubmit:'Passwort speichern',backToLogin:'Zurück zur Anmeldung',"
                      "codeLoginLink:'Mit E-Mail-Code anmelden',codeLoginTitle:'Anmelden ohne Passwort.',codeLoginText:'Wir schicken dir einen einmaligen Code an deine E-Mail-Adresse.',"
                      "sendLink:'Code senden',sending:'Wird gesendet …',"
                      "linkSentTitle:'Schau in dein Postfach.',"
                      "linkSent:'Falls es zu {email} ein Konto gibt, haben wir dir einen sechsstelligen Code geschickt. Gib ihn hier ein.',"
                      "code:'Code aus der E-Mail',codeSubmit:'Anmelden',checking:'Wird geprüft …',"
                      "codeInvalid:'Der Code stimmt nicht oder ist abgelaufen. Prüfe ihn oder fordere einen neuen an.',"
                      "codeShort:'Bitte gib die sechs Ziffern aus der E-Mail ein.',"
                      "resend:'Neu senden',resendIn:'Neu senden in {s} s',resent:'Neue E-Mail ist unterwegs.',"
                      "spamHint:'Keine E-Mail da? Sieh im Spam-Ordner nach. Die Zustellung kann eine Minute dauern.',"
                      "emailInvalid:'Bitte gib eine gültige E-Mail-Adresse ein.',"
                      "linkRate:'Gerade wurden zu viele Anfragen gestellt. Bitte versuche es in ein paar Minuten erneut.',"
                      "linkFail:'Das hat nicht geklappt. Bitte versuche es gleich noch einmal.',"
                      "linkExpired:'Der Link ist abgelaufen oder wurde schon benutzt. Fordere einfach einen neuen Code an.',"
                      "legalLinks:'Es gilt unsere <a href=\\\"/datenschutz.html\\\">Datenschutzerklärung</a>.',"
                      "loginNeeded:'Bitte melde dich erneut an, um weiter zu fragen.',"
                      + TEXTE_ALARM_DE + TEXTE_KONTO_DE + TEXTE_VERLAUF_DE)
TEXTE_ANMELDUNG_EN = ("email:'Email address',emailPlaceholder:'name@example.com',pw:'Password',pwNeu:'Choose a password',"
                      "pwZeigen:'Show password',pwZeigenKurz:'Show',pwVerbergenKurz:'Hide',"
                      "pwRegel:'At least 10 characters. A sentence only you know works best.',pwLeer:'Please enter your password.',"
                      "pwFalsch:'Email address or password is incorrect.',pwSchwach:'This password is too weak. Please choose a longer one.',"
                      "pwGleich:'The new password must differ from the current one.',"
                      "loginSubmit:'Sign in',registerTab:'Register',registerTitle:'Create your account.',registerSubmit:'Create account',"
                      "confirmTitle:'Confirm your email address.',confirmText:'We sent a six-digit code to {email}. Enter it here to finish your account.',"
                      "confirmSubmit:'Confirm',notConfirmed:'Your email address is not confirmed yet. We sent you a new code.',"
                      "alreadyRegistered:'Already registered? Sign in or reset your password.',"
                      "forgotLink:'Forgot password?',forgotTitle:'Reset your password.',forgotText:'Enter your email address. We will send you a code to set a new password.',"
                      "forgotSubmit:'Send code',resetTitle:'Set a new password.',resetText:'If an account exists, we sent a code to {email}. Enter it and choose a new password.',"
                      "newPwText:'Choose a new password for your account.',resetSubmit:'Save password',backToLogin:'Back to sign-in',"
                      "codeLoginLink:'Sign in with an email code',codeLoginTitle:'Sign in without a password.',codeLoginText:'We will email you a one-time code.',"
                      "sendLink:'Send code',sending:'Sending …',"
                      "linkSentTitle:'Check your inbox.',"
                      "linkSent:'If an account exists for {email}, we sent a six-digit code. Enter it here.',"
                      "code:'Code from the email',codeSubmit:'Sign in',checking:'Checking …',"
                      "codeInvalid:'The code is wrong or has expired. Check it or request a new one.',"
                      "codeShort:'Please enter the six digits from the email.',"
                      "resend:'Resend',resendIn:'Resend in {s} s',resent:'A new email is on its way.',"
                      "spamHint:'No email? Check your spam folder. Delivery can take a minute.',"
                      "emailInvalid:'Please enter a valid email address.',"
                      "linkRate:'Too many requests just now. Please try again in a few minutes.',"
                      "linkFail:'That did not work. Please try again in a moment.',"
                      "linkExpired:'The link has expired or was already used. Simply request a new code.',"
                      "legalLinks:'Our <a href=\\\"/datenschutz.html\\\">privacy policy</a> applies.',"
                      "loginNeeded:'Please sign in again to keep asking.',"
                      + TEXTE_ALARM_EN + TEXTE_KONTO_EN + TEXTE_VERLAUF_EN)

# Ersetzt LIVE_JS, wenn die Anmeldung aktiv ist. Sitzung im localStorage, Erneuerung ueber das Refresh-Token.
LIVE_JS_ANMELDUNG = """/* Oeffentlich: zeitversetzter Stand aus /data/stress.json. Aktuell: nur nach Anmeldung ueber /api/aktuell. */
const IT=window.InvestTimer={live:null,pub:result,member:false,chat:null,session:null,
 get view(){return this.member&&this.live?this.live:this.pub},
 setMember(v){this.member=!!v;apply()}};
function apply(){
 const open=$$('#details-panel details').map(e=>e.open),y=window.scrollY;
 result=IT.view;render();
 $$('#details-panel details').forEach((e,i)=>{e.open=!!open[i]});window.scrollTo(0,y);
 document.dispatchEvent(new Event('investtimer:update'));
}
const AUTH=__AUTH__,SKEY='investtimer-sitzung';
const merke=s=>{try{s?localStorage.setItem(SKEY,JSON.stringify(s)):localStorage.removeItem(SKEY)}catch{}};
const gemerkt=()=>{try{return JSON.parse(localStorage.getItem(SKEY)||'null')}catch{return null}};
const sb=(pfad,opt={})=>fetch(AUTH.url+pfad,{...opt,headers:{apikey:AUTH.key,'Content-Type':'application/json',...(opt.headers||{})}});
(()=>{/* Rueckkehr aus dem E-Mail-Link: Sitzung uebernehmen, Adresse bereinigen */
 const h=new URLSearchParams(location.hash.slice(1));if(!h.has('access_token')&&!h.has('error'))return;
 if(h.get('access_token'))merke({access_token:h.get('access_token'),refresh_token:h.get('refresh_token'),
  expires_at:Number(h.get('expires_at'))||Math.floor(Date.now()/1000)+Number(h.get('expires_in')||3600)});
 if(h.get('type')==='recovery')IT.neuesPasswort=true;
 else IT.anmeldeFehler=h.get('error_description')||h.get('error');
 history.replaceState(null,'',location.pathname+location.search);
})();
let erneuern=null;
IT.token=async()=>{
 let s=IT.session||gemerkt();if(!s||!s.access_token)return null;
 if(Date.now()/1000>(s.expires_at||0)-60){
  erneuern=erneuern||sb('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:JSON.stringify({refresh_token:s.refresh_token})})
   .then(r=>r.ok?r.json():Promise.reject(r.status)).finally(()=>{erneuern=null});
  try{const d=await erneuern;s={access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Math.floor(Date.now()/1000)+(d.expires_in||3600)};merke(s)}
  catch(e){if(e===400||e===401){merke(null);IT.session=null}return null}
 }
 IT.session=s;return s.access_token;
};
const fehlerVon=async r=>{const d=await r.json().catch(()=>({}));return d.error_code||d.code||d.error||r.status};
const uebernehme=d=>{const s={access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Math.floor(Date.now()/1000)+(d.expires_in||3600)};
 merke(s);IT.session=s;IT.member=true;lastSeen='';loadLive(true);return s};
const zurueck='?redirect_to='+encodeURIComponent(location.origin+'/');
IT.sendeLink=async email=>{
 const r=await sb('/auth/v1/otp'+zurueck,{method:'POST',body:JSON.stringify({email,create_user:false})});
 if(!r.ok)throw await fehlerVon(r);
};
IT.pruefeCode=async(email,code,typ)=>{
 const r=await sb('/auth/v1/verify',{method:'POST',body:JSON.stringify({type:typ||'email',email,token:code})});
 if(!r.ok)throw await fehlerVon(r);return uebernehme(await r.json());
};
IT.mitPasswort=async(email,password)=>{
 const r=await sb('/auth/v1/token?grant_type=password',{method:'POST',body:JSON.stringify({email,password})});
 if(!r.ok)throw await fehlerVon(r);return uebernehme(await r.json());
};
IT.registrieren=async(email,password)=>{
 const r=await sb('/auth/v1/signup'+zurueck,{method:'POST',body:JSON.stringify({email,password})});
 if(!r.ok)throw await fehlerVon(r);const d=await r.json();if(d.access_token)uebernehme(d);return d;
};
IT.erneutSenden=async(typ,email)=>{
 const r=typ==='recovery'?await sb('/auth/v1/recover'+zurueck,{method:'POST',body:JSON.stringify({email})})
  :typ==='email'?await sb('/auth/v1/otp'+zurueck,{method:'POST',body:JSON.stringify({email,create_user:false})})
  :await sb('/auth/v1/resend'+zurueck,{method:'POST',body:JSON.stringify({type:typ,email})});
 if(!r.ok)throw await fehlerVon(r);
};
IT.passwortSetzen=async(password,nonce)=>{
 const tok=await IT.token();if(!tok)throw 'login';
 const r=await sb('/auth/v1/user',{method:'PUT',headers:{Authorization:'Bearer '+tok},body:JSON.stringify(nonce?{password,nonce}:{password})});
 if(!r.ok)throw await fehlerVon(r);
};
IT.codeFuerAenderung=async()=>{
 const tok=await IT.token();if(!tok)throw 'login';
 const r=await sb('/auth/v1/reauthenticate',{headers:{Authorization:'Bearer '+tok}});if(!r.ok)throw await fehlerVon(r);
};
IT.emailVonSitzung=()=>{try{return JSON.parse(atob((IT.session||gemerkt()).access_token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).email}catch{return ''}};
IT.abmelden=async()=>{
 const s=IT.session||gemerkt();merke(null);IT.session=null;IT.live=null;lastSeen='';IT.setMember(false);
 if(s)sb('/auth/v1/logout',{method:'POST',headers:{Authorization:'Bearer '+s.access_token}}).catch(()=>{});
};
let lastLoad=0,lastSeen='';
function loadLive(force){
 if(!location.protocol.startsWith('http')||(!force&&Date.now()-lastLoad<3e5))return;lastLoad=Date.now();
 document.body.dataset.live='laedt';
 const oeffentlich=fetch('/data/stress.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject())
  .then(d=>normaliseResult(d.publicSnapshot)||normaliseResult(d)).catch(()=>null);
 const aktuell=IT.token().then(tok=>!tok?null:fetch('/api/aktuell',{cache:'no-store',headers:{Authorization:'Bearer '+tok}})
  .then(r=>{if(r.status===401){IT.abmelden();return null}return r.ok?r.json():null}).then(d=>d&&normaliseResult(d))).catch(()=>null);
 Promise.all([oeffentlich,aktuell]).then(([pub,live])=>{
  document.body.dataset.live='fertig';
  if(!pub&&!live){lastLoad=0;return}
  const seen=JSON.stringify([live,pub,!!IT.session]);if(seen===lastSeen)return;
  if(document.querySelector('dialog[open]:not(#access-preview-dialog)')){lastLoad=0;return}
  if(pub)IT.pub=pub;IT.live=live;lastSeen=seen;IT.member=!!(live&&IT.session);apply();
 });
}
IT.loadLive=loadLive;
if(gemerkt())IT.member=true;
loadLive();
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')loadLive()});
window.addEventListener('pageshow',e=>{if(e.persisted)loadLive()});
if(location.protocol.startsWith('http'))fetch('/api/chat',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{IT.chat=!!(d&&d.ok)}).catch(()=>{IT.chat=false});
"""

# Anmeldedialog: E-Mail-Adresse -> Anmeldelink (ersetzt den Knopf "Mitgliederansicht ansehen")
ZUGANG_JS_ANMELDUNG = (ROOT / "tools" / "zugang.js").read_text(encoding="utf-8") + "\n"

NORMALISE_JS = """/* 01 · Ergebnis pruefen (Berechnung laeuft serverseitig) */
function normaliseResult(d){
  if(!d||typeof d!=='object'||!Array.isArray(d.rows)||!Array.isArray(d.blocks))return null;
  const rounded=d.rounded===null?null:Number(d.rounded);
  if(rounded!==null&&!(Number.isInteger(rounded)&&rounded>=0&&rounded<=100))return null;
  const part=r=>r&&typeof r.name==='string'&&Number.isFinite(r.effectiveWeight);
  if(!d.rows.every(part)||!d.blocks.every(part)||!Number.isInteger(d.count))return null;
  return {rounded,count:d.count,rows:d.rows,blocks:d.blocks,asOf:/^\\d{4}-\\d{2}-\\d{2}$/.test(d.asOf)?d.asOf:null};
}
"""

LIVE_JS = """/* Zwei Staende: oeffentlich (zeitversetzt) und aktuell (nach Anmeldung).
   Solange es keine echte Anmeldung gibt, ist das eine Darstellung, keine Zugriffssperre. */
const IT=window.InvestTimer={live:null,pub:result,member:false,chat:null,
 get view(){return this.member&&this.live?this.live:this.pub},
 setMember(v){this.member=!!v;apply()}};
function apply(){
 const open=$$('#details-panel details').map(e=>e.open),y=window.scrollY;
 result=IT.view;render();
 $$('#details-panel details').forEach((e,i)=>{e.open=!!open[i]});window.scrollTo(0,y);
 document.dispatchEvent(new Event('investtimer:update'));
}
let lastLoad=0,lastSeen='';
function loadLive(){
 if(!location.protocol.startsWith('http')||Date.now()-lastLoad<3e5)return;lastLoad=Date.now();
 fetch('/data/stress.json',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
  const live=normaliseResult(d),pub=normaliseResult(d.publicSnapshot),seen=JSON.stringify([live,pub]);
  if(!live||seen===lastSeen)return;
  if(document.querySelector('dialog[open]')){lastLoad=0;return}
  IT.live=live;if(pub)IT.pub=pub;lastSeen=seen;apply();
 }).catch(()=>{lastLoad=0});
}
loadLive();
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')loadLive()});
window.addEventListener('pageshow',e=>{if(e.persisted)loadLive()});
if(location.protocol.startsWith('http'))fetch('/api/chat',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{IT.chat=!!(d&&d.ok)}).catch(()=>{IT.chat=false});
"""

CHAT_JS = """const FRAGEN=__FRAGEN__;
function md(text){
 const i=Math.max(text.lastIndexOf('— Basierend auf:'),text.lastIndexOf('— Wissensbasis:'));
 const body=i>0?text.slice(0,i).replace(/\\s+$/,''):text,bold=l=>esc(l).replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>');
 return body.split(/\\n\\s*\\n/).map(block=>{const lines=block.split('\\n').filter(l=>l.trim());if(!lines.length)return '';
  return lines.map(l=>l.startsWith('## ')?'<p class="chat-heading">'+esc(l.slice(3))+'</p>':l.startsWith('- ')?'<p class="chat-point">• '+bold(l.slice(2))+'</p>':'<p>'+bold(l)+'</p>').join('')}).join('');
}
function turnMarkup(turn){return '<div class="chat-bubble chat-question">'+esc(turn.text)+'</div><div class="chat-bubble chat-answer">'+(turn.answer===null?'<span class="chat-wait" role="status">__MOND_DENKT__'+t('thinking')+'</span>':md(turn.answer))+'</div>'}
function moreMarkup(){
 if(lang()!=='de'||busy||!turns.length)return '';
 const asked=new Set(turns.map(x=>x.text)),list=FRAGEN[tab].fragen.filter(q=>!asked.has(q)).slice(0,3);
 return '<div class="chat-more"><span class="sample-label">'+t('more')+'</span><div class="chat-more-tabs" role="tablist">'+FRAGEN.map((k,i)=>'<button type="button" role="tab" data-tab="'+i+'" aria-selected="'+(i===tab)+'">'+esc(k.kurz)+'</button>').join('')+'</div><div class="assistant-chips">'+list.map(q=>'<button type="button" data-more="'+esc(q)+'">'+esc(q)+' '+arrow+'</button>').join('')+'</div></div>';
}
function renderChat(scroll){
 const typed=$('#assistant-chat-input')?.value||'',top=$('.assistant-messages')?.scrollTop||0;
 chat.innerHTML='<div class="assistant-shell"><header class="assistant-top"><div class="modal-top"><span class="eyebrow">'+t('assistantLabel')+'</span><button id="close-assistant" class="close-button" type="button" aria-label="'+t('back')+'">'+(matchMedia('(max-width:760px)').matches?'←':'×')+'</button></div><h2 id="chat-title" tabindex="-1">'+t('chatTitle')+'</h2><p>'+score()+' / 100 · '+t('stand')+' '+date()+'</p></header><div class="assistant-messages" aria-live="polite">'+turns.map(turnMarkup).join('')+moreMarkup()+'</div><footer class="assistant-bottom"><form class="assistant-composer" id="assistant-chat-form"><input id="assistant-chat-input" aria-label="'+t('placeholder')+'" placeholder="'+t('placeholder')+'" maxlength="300" autocomplete="off" enterkeyhint="send" required><button type="submit" aria-label="'+t('send')+'">↑</button></form><p class="assistant-note">'+t('aiNote')+'</p></footer></div>';
 $('#assistant-chat-input').value=typed;
 const box=$('.assistant-messages');
 if(scroll){const last=box.querySelectorAll('.chat-question');const q=last[last.length-1];box.scrollTop=q?Math.max(0,q.offsetTop-box.offsetTop-12):box.scrollHeight}else box.scrollTop=top;
}
async function ask(text){
 text=String(text||'').trim().slice(0,300);if(busy||!text)return;
 const verlauf=turns.filter(x=>x.answer!==null).slice(-3).flatMap(x=>[{role:'user',content:x.text},{role:'assistant',content:x.answer}]);
 const turn={text,answer:null};turns.push(turn);busy=true;renderChat(true);
 let answer='';
 try{
  const tok=IT.token?await IT.token():null;
  const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json',...(tok?{Authorization:'Bearer '+tok}:{})},body:JSON.stringify({frage:text,verlauf})});
  if(res.status===401){answer=t('loginNeeded');IT.abmelden&&IT.abmelden()}else if(res.status===429)answer=t('limit');else if(!res.ok)throw new Error('HTTP '+res.status);else answer=String((await res.json()).antwort||'');
 }catch{answer=t(IT.chat===false?'unavailable':'offline')}
 turn.answer=answer||t('offline');busy=false;if(chat.open)renderChat(true);
}
function openChat(text,button){
 if(!member){openAccess(button);return}
 opener=button;
 if(!chat.open){renderChat(false);chat.showModal();document.body.classList.add('assistant-open')}
 ask(text);$('#chat-title')?.focus({preventScroll:true});
}
function closeChat(){chat.close();document.body.classList.remove('assistant-open');opener?.focus({preventScroll:true});}
"""

SUBMIT_JS = ("document.addEventListener('submit',e=>{if(!['assistant-entry-form','assistant-chat-form'].includes(e.target.id))return;"
             "e.preventDefault();const input=e.target.querySelector('input');const value=input.value.trim();if(!value)return;input.value='';"
             "if(e.target.id==='assistant-entry-form')openChat(value,e.target.querySelector('button'));else ask(value)});\n")

V12_CSS = """
/* Ergaenzungen fuer den Betrieb: Warten, Antwort-Absaetze, weitere Fragen */
.chat-wait{display:flex;gap:9px;align-items:center;font-size:12px;color:var(--sub)}
.chat-wait i{width:12px;height:12px;border:1.5px solid #bfd3c8;border-top-color:var(--accent);border-radius:50%;animation:chat-spin .8s linear infinite}
@keyframes chat-spin{to{transform:rotate(360deg)}}
.chat-answer .chat-heading{font-weight:600}.chat-answer .chat-point{padding-left:14px;margin-bottom:5px}
.chat-more{flex:none;border-top:1px solid var(--line);padding-top:16px}
.chat-more .sample-label{display:block;color:var(--accent);font-size:10px;letter-spacing:1.3px;margin-bottom:10px}
.chat-more-tabs{display:flex;gap:6px;margin-bottom:10px}
.chat-more-tabs button{font-size:11px;padding:0 13px;min-height:40px;border:1px solid #d7e1d4;border-radius:20px;color:var(--sub)}
.chat-more-tabs button[aria-selected=true]{background:#e5eee4;border-color:#96b5a6;color:var(--text)}
.chat-more .assistant-chips{margin-bottom:0}
.assistant-composer button{height:44px;width:44px}.assistant-composer input{min-height:44px}.market-film-transcript summary{min-height:44px;box-sizing:border-box;padding:15px 0 8px}
.assistant-entry .assistant-note,.assistant-bottom .assistant-note,.member-snapshot-note,.public-access-note,.review-note,.market-film-draft,.snapshot-label{font-size:11px}
.review-switch button{min-height:40px}.header-language{min-width:44px}
@media(prefers-reduced-motion:reduce){.chat-wait i{animation:none}}
"""

KEYS_DE = ("current:'Aktueller Stand',sourceLive:'US-Aktienmarkt · Datenstand ',"
           "aiNote:'Antworten erzeugt eine KI und können Fehler enthalten · Keine Anlageberatung',"
           "thinking:'InvestTimer liest die Daten …',more:'WEITERE FRAGEN',"
           "limit:'Für heute ist das Fragenkontingent erreicht — morgen geht es weiter.',"
           "offline:'Verbindung fehlgeschlagen — bitte in einem Moment erneut versuchen.',"
           "unavailable:'Die KI ist gerade nicht erreichbar.',")
KEYS_EN = ("current:'Latest data',sourceLive:'US stock market · Data as of ',"
           "aiNote:'Answers are generated by AI and may contain errors · Not investment advice',"
           "thinking:'InvestTimer is reading the data …',more:'MORE QUESTIONS',"
           "limit:'Today’s question limit has been reached — please come back tomorrow.',"
           "offline:'Connection failed — please try again in a moment.',"
           "unavailable:'The AI is currently unavailable.',")


def head_meta(preview):
    lines = ['<meta name="application-name" content="InvestTimer">',
             '<meta name="apple-mobile-web-app-title" content="InvestTimer">',
             '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
             '<link rel="manifest" href="/manifest.json">',
             '<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">'
             '<meta name="apple-mobile-web-app-status-bar-style" content="default">']
    if preview:
        lines.append('<meta name="robots" content="noindex,nofollow">')
    else:
        lines += ['<link rel="canonical" href="https://investtimer.net/">',
                  '<meta property="og:type" content="website"><meta property="og:site_name" content="InvestTimer"><meta property="og:locale" content="de_DE">',
                  '<meta property="og:url" content="https://investtimer.net/">',
                  '<meta property="og:title" content="InvestTimer — Marktstress auf einen Blick">',
                  '<meta property="og:description" content="Ein klarer Wert von 0 bis 100. Details auf Wunsch.">',
                  '<meta property="og:image" content="https://investtimer.net/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
                  '<meta name="twitter:card" content="summary_large_image">']
    return "\n".join(lines)


def rechtsseiten(target):
    """Registrierung erst, wenn Impressum und Datenschutzerklaerung ausgeliefert werden."""
    return all((Path(target) / n).is_file() for n in ("impressum.html", "datenschutz.html"))


def main(source, target_dir, preview, anmeldung=None):
    html = Path(source).read_text(encoding="utf-8")
    if anmeldung and not (str(anmeldung.get("url", "")).startswith("https://") and anmeldung.get("anonKey")):
        raise SystemExit("Anmeldedatei braucht url (https://...) und anonKey")
    target = Path(target_dir)
    (target / "media").mkdir(parents=True, exist_ok=True)

    # Ergebnis des gespeicherten Stands (oeffentlicher Rueckfall mit echtem Datum)
    snapshot = json.loads(re.search(
        r'<script type="application/json" id="investtimer-snapshot">(.*?)</script>', html, re.S).group(1))
    result = engine.calculate(engine.metrics_from_rows(snapshot["metricRows"]),
                              engine.config_from_rows(snapshot["configRows"]))
    fallback = {"model": "investtimer-us-market-stress", "asOf": snapshot["asOf"],
                "rounded": result["rounded"], "count": result["count"], "total": result["total"],
                "rows": result["rows"], "blocks": result["blocks"]}
    (ROOT / "server" / "seed_history.json").write_text(
        json.dumps({fallback["asOf"]: fallback}, indent=1) + "\n", encoding="utf-8")

    # Film als Dateien
    film = json.loads(re.search(r'<script type="application/json" id="investtimer-film-config">(.*?)</script>', html, re.S).group(1))
    (target / "media" / "invest-timer.mp4").write_bytes(base64.b64decode(film["src"].split(",", 1)[1]))
    (target / "media" / "invest-timer-poster.jpg").write_bytes(base64.b64decode(film["poster"].split(",", 1)[1]))
    html = sub_once(html, r'<script type="application/json" id="investtimer-film-config">.*?</script>',
                    '<script type="application/json" id="investtimer-film-config">'
                    '{"src":"/media/invest-timer.mp4","poster":"/media/invest-timer-poster.jpg"}</script>', "Film-Daten")

    # Kopf
    html = sub_once(html, r"<!--\nINVESTTIMER · COMPLETE SINGLE-FILE UI EXPORT.*?-->",
                    "<!-- InvestTimer · investtimer.net · Quelle: UI-Export v1.2 (Signalbogen) -->", "Kopfkommentar")
    html = once(html, " Clarity mit dem Volafly-Modell aus 14 Komponenten und gespeichertem Datenstand.",
                " 14 Bestandteile, ein Wert.", "Beschreibung")
    html = once(html, "connect-src 'none'", "connect-src 'self'%s; manifest-src 'self'; worker-src 'self'" % (
        " " + anmeldung["url"].rstrip("/") if anmeldung else ""), "CSP Abrufe")
    html = once(html, "img-src data:;", "img-src 'self' data:;", "CSP Bilder")
    html = once(html, "media-src data:;", "media-src 'self';", "CSP Film")
    html = once(html, '<meta name="application-name" content="InvestTimer">', head_meta(preview), "Kopf-Meta")
    html = sub_once(html, r'(?<=<script type="application/json" id="investtimer-export-manifest">).*?(?=</script>)',
                    "\n" + json.dumps({"artifact": "InvestTimer UI", "exportVersion": "1.2", "languages": ["de", "en"],
                                       "data": "/data/stress.json", "chat": "/api/chat"}, indent=1) + "\n", "Manifest")

    # Daten: Rohwerte und Rechenkern raus, Ergebnis rein
    html = sub_once(
        html,
        r'<!-- 03 · Saved, replaceable data snapshot -->\n<script type="application/json" id="investtimer-snapshot">.*?</script>',
        '<!-- 03 · Oeffentlicher Stand als Rueckfall, falls /data/stress.json nicht erreichbar ist -->\n'
        '<script type="application/json" id="investtimer-result">\n%s\n</script>' % json.dumps(fallback, indent=1),
        "Snapshot-Block")
    html = sub_once(html, r"/\* INVESTTIMER EXPORT v1\.0 · no imports, no build step, no network calls\. \*/",
                    "/* InvestTimer · kein Build-Schritt. Werte kommen aus /data/stress.json. */", "Skriptkommentar")
    html = sub_once(html, r"const evaluateSnapshot = \(\(\) => \{.*?return evaluateSnapshot;\n\}\)\(\);\n", NORMALISE_JS, "Rechenkern")
    html = sub_once(html, r"// Plain-language summaries grounded in the user's Drive knowledge base\.\n// Source mapping and editorial choices are recorded in docs/plain-language-ui\.md\.\n",
                    "", "Erklaerungs-Kommentar")

    # Datumsangaben der Hauptansicht
    html = once(html, "databody:'Diese Ansicht verwendet den gespeicherten Datenstand vom 15. November 2026. Eine laufende Aktualisierung und ein historischer Verlauf sind noch nicht verbunden.'",
                "databody:'Datenstand: {datelong}. Der Wert wird regelmäßig aktualisiert. Den Tagesverlauf siehst du nach der Anmeldung oben im Detailbereich.',"
                "databodyPublic:'Historischer Wert vom {datelong}. Den aktuellen Marktstress siehst du nach der Anmeldung.'", "databody de")
    html = once(html, "databody:'This view uses the saved data snapshot from 15 November 2026. Continuous updates and a historical chart are not connected yet.'",
                "databody:'Data as of {datelong}. The score is updated regularly. After sign-in, the daily history appears at the top of this section.',"
                "databodyPublic:'Historical reading from {datelong}. The latest market stress is available after sign-in.'", "databody en")
    html = once(html, "<p>${t('databody')}</p>", "<p>${t(window.InvestTimer?.member?'databody':'databodyPublic')}</p>", "databody Auswahl")
    html = once(html, "timestamp:'US-Aktienmarkt · Datenstand 15. Nov. 2026'", "timestamp:'US-Aktienmarkt · Datenstand {date}'", "timestamp de")
    html = once(html, "timestamp:'US stock market · Data as of 15 Nov 2026'", "timestamp:'US stock market · Data as of {date}'", "timestamp en")
    html = once(html, "const t=k=>copy[state.lang][k];\nconst number=",
                "const dateLabel=month=>{if(!result?.asOf)return '—';const [y,m,d]=result.asOf.split('-').map(Number);"
                "return new Date(Date.UTC(y,m-1,d)).toLocaleDateString(state.lang==='de'?'de-DE':'en-GB',{day:'numeric',month,year:'numeric',timeZone:'UTC'})};\n"
                "const t=k=>{const v=copy[state.lang][k];return typeof v==='string'?v.replace('{datelong}',()=>dateLabel('long')).replace('{date}',()=>dateLabel('short')):v};\n"
                "const number=", "t()")
    html = once(html, "try{result=evaluateSnapshot(JSON.parse(document.getElementById('investtimer-snapshot').textContent))}catch{result=null}",
                "try{result=normaliseResult(JSON.parse(document.getElementById('investtimer-result').textContent))}catch{result=null}", "Ergebnis laden")
    live_js = LIVE_JS
    if anmeldung:
        live_js = LIVE_JS_ANMELDUNG.replace("__AUTH__", json.dumps(
            {"url": anmeldung["url"].rstrip("/"), "key": anmeldung["anonKey"]}))
    html = once(html, "render();\n\n})();\n(() => {\n/* 04 ·", "render();\n" + live_js + "\n})();\n(() => {\n/* 04 ·", "Live-Abruf")

    # Signalbogen: Halbmond fuellt sich (gleicher Baustein wie in build_public.py)
    html = sub_once(html, r"function updateGauge\(\)\{.*?\n\}\nfunction renderModule\(\)\{",
                    GAUGE_JS + "function renderModule(){", "updateGauge")
    html = once(html, "new MutationObserver(updateGauge).observe(score,",
                "gaugeObserver=new MutationObserver(updateGauge);gaugeObserver.observe(score,", "Gauge-Observer")

    # Zugangs- und KI-Ansicht an echte Daten und den Chat anschliessen
    html = once(html, "/* UI concept only. No authentication, live feed or remote AI service. */",
                "/* Oeffentliche Ansicht und Ansicht nach Login. Noch keine echte Anmeldung: der Wechsel ist eine Darstellung. */", "Zugang Kommentar")
    html = once(html, "const snapshot=JSON.parse($('#investtimer-snapshot').textContent);\n"
                      "const manifest=JSON.parse($('#investtimer-export-manifest').textContent);\n"
                      "const score=manifest.snapshotScore;\n",
                "const IT=window.InvestTimer;\nconst view=()=>IT.view||{};\nconst score=()=>view().rounded??'—';\n", "Zugang Daten")
    html = once(html, "let member=false, opener=null, question='', answerKind='reading', turns=[];",
                "let member=false, opener=null, question='', turns=[], busy=false, tab=0;", "Zugang Zustand")
    html = once(html, "new Date(snapshot.asOf+'T12:00:00Z')", "new Date((view().asOf||'1970-01-01')+'T12:00:00Z')", "Zugang Datum")
    if html.count("+score+' / 100 · '") != 2:
        raise SystemExit("Erwartete zwei Stellen fuer die Wertanzeige im KI-Bereich")
    html = html.replace("+score+' / 100 · '", "+score()+' / 100 · '")
    if html.count("'+score+'") != 4:
        raise SystemExit("Erwartete vier Textstellen mit dem Wert")
    html = html.replace("'+score+'", "{score}")
    html = once(html, "const t=k=>c[lang()][k];", "const t=k=>String(c[lang()][k]).replace('{score}',score());", "Zugang t()")
    html = once(html, "const c={de:{login:'Anmelden',", "const c={de:{" + KEYS_DE + TEXTE_ANMELDUNG_DE + "login:'Anmelden',", "Texte de")
    html = once(html, "},en:{login:'Sign in',logout:'Sign out',preview:", "},en:{" + KEYS_EN + TEXTE_ANMELDUNG_EN + "login:'Sign in',logout:'Sign out',preview:", "Texte en")
    # KI-Zeichen: Halbmond statt Netz-Symbol
    html = sub_once(html, r"const orbit='<svg class=\"assistant-orbit\".*?</svg>';",
                    "const orbit='" + MOND.format(cls="assistant-orbit ki-halbmond") + "';", "KI-Zeichen")
    if anmeldung:
        html = once(html, "function update(){", "function update(){member=!!IT.member;", "Zugang folgt Anmeldung")
        html = once(html, "if(member&&b.id==='account-login')switchView(false);else openAccess(b);",
                    "if(member&&b.id==='account-login')IT.abmelden();else{IT.zugangModus&&IT.zugangModus(b.id==='account-login'?'anmelden':'registrieren');openAccess(b)}", "Abmelden")
        html = once(html, "$('.app').after(review);", "/* Entwurfsansicht entfaellt mit echter Anmeldung */", "Entwurfsansicht")
        offen = rechtsseiten(target)
        html = sub_once(html, r"function renderAccess\(\)\{access\.innerHTML=[^\n]*\n",
                        ZUGANG_JS_ANMELDUNG.replace("REGISTRIERUNG_RECHT", "true" if offen else "false")
                        .replace("CODE_AKTIV", "true" if anmeldung.get("code", True) else "false"), "Anmeldedialog")
        if not offen:
            html = once(html, "<body>", '<body class="ohne-registrierung">', "Registrierung aus")
            html = once(html, "databodyPublic:'Historischer Wert vom {datelong}. Den aktuellen Marktstress siehst du nach der Anmeldung.'",
                        "databodyPublic:'Historischer Wert vom {datelong}.'", "databodyPublic de ohne Registrierung")
            html = once(html, "databodyPublic:'Historical reading from {datelong}. The latest market stress is available after sign-in.'",
                        "databodyPublic:'Historical reading from {datelong}.'", "databodyPublic en ohne Registrierung")
        else:
            html = once(html, '<span data-i18n="tagline">Marktstress verstehen.</span></footer>',
                        '<span data-i18n="tagline">Marktstress verstehen.</span>'
                        '<nav class="rechtliches"><a href="/impressum.html">Impressum</a> · <a href="/datenschutz.html">Datenschutz</a>'
                        + (' · <a href="/vertrag-kuendigen.html">Verträge hier kündigen</a> · <a href="/vertrag-widerrufen.html">Vertrag widerrufen</a>'
                           if json.loads((ROOT / "deploy" / "abo.json").read_text()).get("vertragsseiten") else "")
                        + '</nav></footer>',
                        "Fusslinks Rechtstexte")
        print("Registrierung: %s" % ("offen" if offen else "ausgeblendet (Impressum/Datenschutz fehlen)"))
    html = once(html, "stamp.textContent=(member?t('saved'):t('preview'))+' · '+date();stamp.title=member?t('memberNote'):t('noCurrent');",
                "stamp.textContent=(member&&IT.live?t('current'):t('preview'))+' · '+date();stamp.title=member&&IT.live?'':t('noCurrent');", "Stempel")
    html = once(html, "memberNote.textContent=t('memberNote');memberNote.hidden=!member;", "memberNote.hidden=true;", "Mitglieder-Hinweis")
    html = once(html, "$('.app-footer [data-i18n=\"timestamp\"]').textContent=t('source')+date();",
                "$('.app-footer [data-i18n=\"timestamp\"]').textContent=t(member?'sourceLive':'source')+date();", "Fusszeile")
    if html.count("t('chatNote')") != 2 or html.count('maxlength="2000"') != 2:
        raise SystemExit("Erwartete je zwei Stellen fuer chatNote und maxlength")
    html = html.replace("t('chatNote')", "t('aiNote')").replace('maxlength="2000"', 'maxlength="300"')
    html = once(html, "function switchView(value){member=value;question='';update();",
                "function switchView(value){member=value;question='';IT.setMember(value);update();", "Ansichtswechsel")

    # Texte des Entwurfs, die im Betrieb nicht mehr vorkommen (Beispielantworten, Vorschau-Hinweise)
    before, access = html.split('<script id="investtimer-access-ui">', 1)
    access, removed = re.subn(
        r"(?<=[,{])(?:sample|answer1|answer1b|answer2|answer2b|freeTitle|free|chatNote|memberNote|saved):'(?:[^'\\]|\\.)*',", "", access)
    if removed != 20:
        raise SystemExit("Erwartete 20 entfernte Entwurfstexte, gefunden %d" % removed)
    html = before + '<script id="investtimer-access-ui">' + access

    fragen = json.loads((ROOT / "volafly-api" / "investtimer_fragen.json").read_text(encoding="utf-8"))
    kategorien = [{"kurz": k["kurz"], "fragen": [f["frage"] for f in k["fragen"]]} for k in fragen["kategorien"]]
    html = sub_once(html, r"function answerMarkup\(kind\)\{.*?function closeChat\(\)\{[^\n]*\n",
                    CHAT_JS.replace("__FRAGEN__", json.dumps(kategorien, ensure_ascii=False)).replace("__MOND_DENKT__", MOND.format(cls="ki-halbmond")), "Chat-Kern")
    html = sub_once(html, r"document\.addEventListener\('submit',e=>\{if\(!\['assistant-entry-form'[^\n]*\n", SUBMIT_JS, "Chat-Absenden")
    html = once(html, "else if(b.dataset.ask)openChat(b.dataset.ask,null,b);",
                "else if(b.dataset.ask)openChat(t(b.dataset.ask==='composition'?'question2':'question1'),b);"
                "else if(b.dataset.more!==undefined)ask(b.dataset.more);"
                "else if(b.dataset.tab!==undefined){tab=Number(b.dataset.tab);renderChat(false);$('.assistant-messages').scrollTop=1e6}", "Chat-Klicks")
    html = once(html, "new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});\nupdate();",
                "new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});\n"
                "document.addEventListener('investtimer:update',update);\nupdate();" + (
                    "\nif(IT.neuesPasswort){IT.zugangModus('neu');openAccess(null)}else if(IT.anmeldeFehler){IT.zugangModus('code-email');zugangsFehler=t('linkExpired');openAccess(null)}\n" + ALARM_JS + "\n" + KONTO_JS
                    if anmeldung else ""), "Zugang Aktualisierung")

    # Stile: Mobil-Nachschaerfung hinter die Export-Stile, Ergaenzungen hinter die Zugangs-Stile
    head, rest = html.split('<style id="investtimer-access-style">', 1)
    head = once(head, "</style>", MOBILE_CSS + GAUGE_CSS + "</style>", "Mobil-CSS")
    access_css, rest = rest.split("</style>", 1)
    html = head + '<style id="investtimer-access-style">' + access_css + V12_CSS + HALBMOND_CSS + (ANMELDUNG_CSS + KONTO_CSS if anmeldung else "") + "</style>" + rest

    for leftover in ("investtimer-snapshot", "evaluateSnapshot", "metricRows", "configRows", "Fear_Greed_Index",
                     "snapshotScore", "sourceLibraryFileId", "data:video", "answerKind", "BEISPIELANTWORT"):
        if leftover in html:
            raise SystemExit("Rest gefunden: " + leftover)
    html = entwurfsreste_entfernen(html)
    html = base64_auslagern(html, target)
    (target / "index.html").write_text(html, encoding="utf-8")
    print("ok: oeffentlicher Rueckfall %s vom %s, %d Bytes HTML, Film %d Bytes" % (
        fallback["rounded"], fallback["asOf"], len(html.encode()), (target / "media" / "invest-timer.mp4").stat().st_size))



# Entwurfsreste der UI-Vorlage (Demo-Dialoge, Entwurfsschalter, Export-Manifest) aus der ausgelieferten Seite entfernen.
# Die Demo-Dialoge sind seit der echten Anmeldung nicht mehr erreichbar; ihre Texte werden neutral, Kennungen umbenannt.
ENTWURF_TEXTE = {  # Schluessel: (de, en)
    "alertdemo": ("", ""), "savealert": ("Alarm speichern", "Save alert"), "saved": ("Alarm gespeichert.", "Alert saved."),
    "resumed": ("Alarm aktiviert.", "Alert activated."), "stored": ("", ""),
    "maxalerts": ("Du kannst bis zu fünf Alarme anlegen.", "You can create up to five alerts."),
    "localonly": ("Alarm gespeichert.", "Alert saved."), "confirm": ("Bestätigen", "Confirm"), "demo": ("", ""),
    "savedTitle": ("Deine Auswahl.", "Your selection."), "hint": ("", ""), "accessDemo": ("", ""),
    "review": ("", ""), "public": ("", ""), "members": ("", ""), "reviewNote": ("", ""),
    "accessAction": ("Anmelden", "Sign in"), "preview": ("Historischer Einblick", "Historical reading"),
    "draft": ("Historische Stresswerte im Film noch nicht geprüft", "Historical stress values in the film not yet verified"),
}
ENTWURF_WORTE = re.compile(r"(?i)demo|entwurf|vorschau|beispielantwort")


def entwurfsreste_entfernen(html):
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r"/\*(?:(?!\*/).)*?\*/", lambda m: "" if ENTWURF_WORTE.search(m.group(0)) else m.group(0), html, flags=re.S)
    html = re.sub(r'<script type="application/json" id="investtimer-export-manifest">.*?</script>', "", html, flags=re.S)
    html = re.sub(r'<meta name="investtimer-export-version"[^>]*>', "", html)
    for schluessel, (de, en) in ENTWURF_TEXTE.items():
        treffer = list(re.finditer(r"(?<=[,{])%s:'(?:[^'\\]|\\.)*'" % schluessel, html))
        for m, wert in reversed(list(zip(treffer, [de, en]))):
            html = html[:m.start()] + "%s:'%s'" % (schluessel, wert) + html[m.end():]
    for alt, neu in (("investtimer-standalone-v1-demo-alerts", "investtimer-alarme-lokal"), ("accessDemo", "accessHinweis"),
                     ("alertdemo", "alerthinweis"), ("demo-note", "kopf-hinweis"), (">Demo-Alarm speichern<", ">Alarm speichern<"),
                     ("${t('demo')}", "${t('demoText')}".replace("demo", "zusatz")), (",demo:''", ",zusatz:''"),
                     ("/* Entwurfsansicht entfaellt mit echter Anmeldung */", ""), ("'UI preview states'", "'Ansicht'")):
        html = html.replace(alt, neu)
    html = html.replace("</style>", ".ui-review{display:none!important}</style>", 1)
    rest = [html[max(0, m.start() - 60):m.end() + 60] for m in ENTWURF_WORTE.finditer(html)]
    if rest:
        raise SystemExit("Entwurfsreste in der Seite:\n" + "\n".join(rest[:20]))
    return html


def base64_auslagern(html, target):
    """Schriften und Bilder aus data:-URIs als eigene Dateien unter /media/ ausliefern (Name = Inhalts-Hash)."""
    import hashlib
    endung = {"font/woff2": "woff2", "font/ttf": "ttf", "image/svg+xml": "svg", "image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4"}
    def ersetze(m):
        daten = base64.b64decode(m.group(2))
        name = "%s.%s" % (hashlib.sha256(daten).hexdigest()[:12], endung[m.group(1)])
        (target / "media" / name).write_bytes(daten)
        return "/media/" + name
    html = re.sub(r"data:([a-z/0-9.+-]+);base64,([A-Za-z0-9+/=]+)", ersetze, html)
    for alt, neu in (("img-src 'self' data:", "img-src 'self'"), ("font-src data:", "font-src 'self'")):
        if alt not in html:
            raise SystemExit("CSP-Stelle fehlt: " + alt)
        html = html.replace(alt, neu)
    if re.search(r"(?i)base64,", html):
        raise SystemExit("Base64 in der Seite")
    return html

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    datei = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--anmeldung=")), None)
    main(args[0], args[1], "--vorschau" in sys.argv, json.loads(Path(datei).read_text()) if datei else None)
