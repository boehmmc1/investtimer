# InvestTimer Premium, Abos und iOS-App – Umsetzungsstand

Stand: 17.11.2026. Grundlage: Feature-Requests FR-001 bis FR-032.

## Kurzfassung

Fertig und live:
- **Konto:** Bereich „Mein Konto“ mit Abo-Status und Kontolöschung (Website und App).
- **KI-Kontingent:** Es wird je Konto auf dem Server gezählt.
- **Push:** Web-Push für Website und Web-App, Apple-Push für die iOS-App.

Fertig, aber ausgeschaltet:
- **Abo-Grundlage:** Premium-Prüfung auf dem Server, Paywall, Stripe-Checkout, Kundenportal, Anbindung von RevenueCat.
- **Schalter:** Alles hängt an zwei Schaltern. Eingeschaltet wird erst, wenn die Konten bei Stripe, RevenueCat und Apple eingerichtet sind und die Rechtsfragen geklärt sind.

Gebaut, aber noch nicht eingereicht:
- **iOS-App (Capacitor 8):** Das Projekt liegt in `app/`. GitHub baut es bei jeder Änderung ohne Signatur für den Simulator.
- **Fehlt bis zur Einreichung:** das Apple-Entwicklerkonto, die Signatur und TestFlight.

## Architektur

```
Website (public/index.html) ──┐
                              ├── /api/* (nginx) ── Volafly-API (FastAPI, Port 8100)
iOS-App (app/, Capacitor) ────┘        │                 ├─ investtimer_konto.py   Premium-Stand, KI-Kontingent, Löschung
   gleiche index.html                  │                 ├─ investtimer_alarme.py  Alarme, Push-Geräte (Web-Push + APNs)
   + app-bruecke.js                    │                 └─ Supabase Auth          ein Konto für Web und App
                                       │
Stripe (Web-Kauf) ──Webhook──> /api/abo/stripe-webhook ──> RevenueCat (/v1/receipts)
Apple (App-Kauf) ──────────────────────────────────────> RevenueCat
RevenueCat ──Webhook──> /api/abo/revenuecat-webhook ──> konto.db (Zwischenspeicher)
```

**Konto und Kauf**
- **Eine Nutzer-ID:** Die Supabase-Nutzer-ID ist zugleich die App-User-ID bei RevenueCat und steht in den Stripe-Metadaten (`app_user_id`).
- **Eine Berechtigung:** Beide Tarife und beide Kanäle schalten dieselbe Berechtigung `premium` frei.
- **Prüfung immer auf dem Server:** Die Funktion `ist_premium(uid)` liest `konto.db`.
  - Den Stand holt der Server bei jedem Webhook, nach einem Kauf und nach einer Wiederherstellung neu von RevenueCat (`GET /v1/subscribers`).
  - Ist RevenueCat nicht erreichbar, gilt der zuletzt gespeicherte Stand bis zu seinem Ablaufdatum.
- **Kein Doppelabo:** Der Checkout lehnt ab, solange Premium läuft (`schon_premium`). Die App zeigt Premium-Nutzern kein Kaufangebot.
- **Testphase nur einmal:**
  - Merkmal je Konto: `test_genutzt`, aus RevenueCat bzw. Stripe.
  - Merkmal je E-Mail: ein SHA-256-Hash, damit nach Löschung und Neuanmeldung keine zweite Testphase entsteht.
  - Apple prüft die Berechtigung für das Einführungsangebot selbst.

**Kündigen und Löschen**
- **Kündigen:**
  - Web-Abo: Stripe-Kundenportal.
  - Apple-Abo: Abo-Verwaltung der Apple-ID (in der App über `showManageSubscriptions`).
  - In der App wird für Web-Abos nur auf die Website verwiesen, wegen der Apple-Regel 3.1.1.
- **Kontolöschung:** Sie wird abgelehnt, solange ein Abo sich automatisch verlängert (`abo_aktiv`), sonst liefe die Abbuchung weiter. Gelöscht werden:
  - der Supabase-Nutzer,
  - Alarme und Push-Geräte,
  - Abo-Stand und KI-Zähler,
  - der Kunde bei RevenueCat.

  Kaufbelege bleiben bei Apple bzw. Stripe.

## Schalter und Zugangsdaten

| Ort | Eintrag | Wirkung |
|---|---|---|
| `/root/volafly-chat/.env` | `IT_PREMIUM_PFLICHT=1` | Aktueller Wert, KI und neue Alarme nur mit Premium; Push nur an Premium-Konten. **Derzeit aus** (Anmeldung reicht). |
| `/root/volafly-chat/.env` | `IT_PAYWALL=1` | Tarifauswahl und Checkout auf der Website. **Derzeit aus.** |
| `/root/volafly-chat/.env` | `IT_ZAHLUNG_LIVE=1` | Erlaubt Stripe-Live-Schlüssel. Ohne den Schalter werden nur `sk_test_`/`rk_test_` angenommen. |
| `/root/volafly-chat/.env` | `IT_KI_TAG`, `IT_KI_MONAT` | KI-Fragen je Konto, Standard 10 pro Tag und 200 pro Monat. |
| `/root/.investtimer/stripe.json` (0600) | `{"secret", "webhook", "preise": {"monatlich", "jaehrlich"}, "steuer_automatisch", "agb_zustimmung"}` | Stripe-Zugang. Fehlt die Datei, sind Checkout und Webhook aus. |
| `/root/.investtimer/revenuecat.json` (0600) | `{"secret", "webhook", "stripe_public"}` | Abruf von RevenueCat, Prüfung des Webhooks, Meldung von Stripe-Käufen. |
| `/root/.investtimer/apns.json` (0600) | `{"p8", "key_id", "team_id", "bundle", "sandbox"}` | Apple-Push für die iOS-App. |
| `app/app.json` | `revenuecatApple` | Öffentlicher RevenueCat-SDK-Schlüssel (`appl_…`) für den Kauf in der App. Kein Geheimnis. |

Die Schalter liest die API alle 30 Sekunden neu, ein Neustart ist nicht nötig.

## Externe Einrichtung (braucht Michel)

1. **Apple Developer Program** (99 $ pro Jahr):
   - App-ID `net.investtimer.app` mit Push anlegen.
   - Einen APNs-Schlüssel (.p8) erzeugen und auf dem Server nach `apns.json` legen.
   - In App Store Connect zwei Abos in einer Abo-Gruppe anlegen: `net.investtimer.premium.monthly` (4,99 €) und `net.investtimer.premium.yearly` (39,99 €), jeweils mit 7 Tagen gratis als Einführungsangebot.
   - Den Vertrag für kostenpflichtige Apps (Paid Apps Agreement) abschließen und Bank- und Steuerdaten hinterlegen.
2. **Stripe**, zuerst im Testmodus:
   - Produkt „InvestTimer Premium“ mit zwei Preisen anlegen. Die Lookup-Keys bzw. Produkt-IDs sind `investtimer_premium_monthly` und `investtimer_premium_yearly`.
   - Das Kundenportal einschalten: Kündigen, Zahlungsmethode, Rechnungen, Tarifwechsel.
   - Den Webhook `https://investtimer.net/api/abo/stripe-webhook` für das Ereignis `checkout.session.completed` anlegen.
   - Die Steuerfrage klären (Stripe Tax oder Merchant of Record), siehe TAX-Punkte.
3. **RevenueCat:**
   - Projekt anlegen und die Apps „App Store“ und „Stripe“ verbinden.
   - Die Berechtigung `premium` anlegen und beide Produkte je Kanal zuordnen.
   - Das Offering `default` mit den Paketen `$rc_monthly` und `$rc_annual` anlegen.
   - Den Webhook `https://investtimer.net/api/abo/revenuecat-webhook` mit eigenem Authorization-Wert eintragen.
   - Den Secret-Key (`sk_…`), den Stripe-Public-Key und den Apple-SDK-Schlüssel an Claude geben bzw. auf dem Server ablegen.
4. **Rechtstexte:** Für Abo-Bedingungen (`/agb.html`), Widerrufsbelehrung, Kündigungsbutton nach § 312k BGB und die Datenschutz-Abschnitte zu Stripe, RevenueCat und Apple geht zuerst eine Prüfung an den Prüfpartner, danach an einen Anwalt.

## Status je Feature-Request

Legende: ✅ fertig · 🟡 teilweise / hinter Schalter · ⛔ offen (extern oder Recht)

| FR | Thema | Status | Was steht / was fehlt |
|---|---|---|---|
| 001 | iOS-App, gleiche Codebasis | 🟡 | Capacitor 8 in `app/`, die App nutzt dieselbe `index.html` und dieselbe API; GitHub baut sie für den Simulator. Es fehlen Signatur und Gerätetest (Apple-Konto). |
| 002 | App-Store-Konformität | 🟡 | Native Push (APNs), Apple-Kauf, Kontolöschung in der App, Datenschutz-Manifest, kein Web-Kauf-Link in der App. Es fehlen die Datenschutzangaben in App Store Connect und der Review. |
| 003 | Mobile Oberfläche | 🟡 | Die mobil geprüfte Oberfläche ist im Web übernommen; Wert steht oben, Dialoge als Bottom-Sheet. Dark Mode richtet sich nach der Website. Kein Test auf echtem Gerät. |
| 004 | Zentrales Konto | 🟡 | Ein Supabase-Konto für Web und App (E-Mail-Code). Sign in with Apple und Google sind nicht gebaut: Ohne Drittanbieter-Login verlangt Apple keinen Apple-Login. |
| 005 | Zentrale Premium-Berechtigung | 🟡 | Serverseitige Prüfung, gleiche Berechtigung über alle Kanäle, Erstattung und Zahlungsproblem werden behandelt. Ist hinter dem Schalter; es fehlen die Konten. |
| 006 | Zwei Tarife | 🟡 | Paywall mit 4,99 €/Monat und 39,99 €/Jahr, Jahresabo hervorgehoben. Preise stehen beim Anbieter, spätere Änderungen sind dort möglich. |
| 007 | 7 Tage Test | 🟡 | Stripe: `trial_period_days=7` mit Zahlungsdaten vorab. Apple: Einführungsangebot. Die Paywall nennt Preis, Datum der ersten Abbuchung und Verlängerung. |
| 008 | Testphase einmal | 🟡 | Je Konto über RevenueCat, je E-Mail als Hash. Apple-Regeln gelten zusätzlich. |
| 009 | Kostenloser Zugang | ✅/🟡 | Ohne Anmeldung gibt es den 7 Tage alten Wert mit Datum (live). Die Sperre für angemeldete Nutzer ohne Premium hängt am Schalter. **Offen:** `history.json` ist öffentlich, die ganze Historie also noch nicht Premium. |
| 010 | Paywall | 🟡 | Gebaut, mobil und Desktop geprüft. Der Link `/agb.html` führt ins Leere, bis die Abo-Bedingungen da sind. |
| 011 | Stripe | 🟡 | Checkout, Kundenportal und Webhook mit Signaturprüfung sind gebaut. Kein Testlauf mit echtem Stripe-Testkonto. Steuer: Schalter vorhanden. |
| 012 | Apple In-App-Kauf | 🟡 | RevenueCat-Plugin mit Kauf, Wiederherstellen und Abo-Verwaltung; im Browser nachgestellt getestet. Produkte in App Store Connect fehlen. |
| 013 | RevenueCat | 🟡 | Webhook (idempotent, Reihenfolge-sicher), Abruf des Abonnenten, Kundenlöschung. Konto fehlt. Customer Center nicht genutzt, die eigene Ansicht deckt es ab. |
| 014 | Jederzeit kündigen | 🟡 | Über das Stripe-Portal bzw. Apple, Status-Abgleich über RevenueCat. Kündigungsbestätigung schicken Stripe bzw. Apple. |
| 015 | Verbraucherrecht | ⛔ | § 309 Nr. 9 und § 312k BGB (Kündigungsbutton ohne Login), Widerruf bei digitalen Inhalten und Bestellknopf. Zuerst Prüfpartner, dann Anwalt. |
| 016 | Mein Abonnement | ✅ | Tarif, Preis, Status, Kanal, Beginn, nächste Verlängerung bzw. Ende, Verlängerung, Testtage und KI-Zähler. Die Aktionen laufen je Kanal über Stripe-Portal, Apple oder Google. |
| 017 | Richtige Kündigungsverwaltung | ✅ | Der Kanal wird erkannt und je nach Kanal die passende Verwaltung geöffnet. |
| 018 | Tarifwechsel | 🟡 | Über das Stripe-Portal bzw. Apple (dort wird anteilig verrechnet); als `PRODUCT_CHANGE` synchronisiert. |
| 019 | Doppelabo verhindern | 🟡 | Serverseitige Sperre, kein Kaufangebot für Premium-Nutzer. Bestehende Doppelabos: manuell erstatten (Prozess unten). |
| 020 | Mails zur Testphase | ⛔ | Bewusst noch nicht gebaut. Stripe kann die Erinnerung vor Testende selbst senden, Apple informiert selbst. Eigene Mails (Resend) erst nach der Rechtsprüfung, sonst doppelt. |
| 021 | Push zum Marktstress | ✅/🟡 | Eigene Schwellen, Push über Web-Push (live, getestet) und APNs (gebaut, Server erreicht Apple). Nur einmal am Tag. Für die App fehlt der APNs-Schlüssel. |
| 022 | KI als Premium | 🟡 | Die Sperre hängt am Schalter. Die KI-Infrastruktur ist unverändert. |
| 023 | KI-Limits | ✅ | Zähler je Konto und Tag in SQLite (gilt für Web und App), Tages- und Monatsgrenze per `.env`, dazu die bisherigen IP- und Gesamtgrenzen. |
| 024 | Datenschutz & Löschung | 🟡 | Löschung in Web und App ist live; die Datenschutzerklärung ist angepasst. Abschnitte zu Stripe, RevenueCat und Apple-Kauf erst mit dem Start. |
| 025 | Recht & Disclaimer | ⛔ | Impressum steht. Abo-Bedingungen, DSA- und Apple-Händlerangaben und die FIN-Einordnung der KI sind offen. |
| 026 | Tests | 🟡 | `tests/test_konto.py` deckt alle 18 Szenarien gegen die Berechtigungslogik ab. Browsertests: Web-Dialog, App-Ablauf (nachgestellt), echte Löschung. Es fehlen die End-to-End-Tests mit Stripe-Test und RevenueCat-Sandbox. |
| 027 | App-Store-Vorbereitung | 🟡 | Bundle-ID, Name, Icon, Splash, Datenschutz-Manifest und Build-Prozess (`docs/ios-app.md`). Es fehlen Konto, Screenshots, Beschreibung im Store und TestFlight. |
| 028 | Geringe Fixkosten | ✅ | Kein neues Backend, SQLite auf dem vorhandenen Server. Laufende Kosten: Apple 99 $/Jahr, Stripe ca. 1,5 % + 0,25 € je Zahlung, RevenueCat frei bis 2.500 $ Monatsumsatz. |
| 029 | Android vorbereitet | 🟡 | Capacitor und RevenueCat unterstützen Android, der Kanal `google` ist in der Logik schon vorgesehen. Der Android-Push braucht FCM. |
| 030 | Bestandsaufnahme | ✅ | Diese Datei. |
| 031 | Phasen | – | Phase 1 fertig. Phase 2 und 3 gebaut, warten auf Konten und Recht. Phase 4 größtenteils fertig. |
| 032 | Definition of Done | – | Siehe offene Punkte. |

## Offene Punkte und Risiken

- **Recht (vor jedem echten Verkauf):**
  - LAW: Bestellknopf, Widerruf, Kündigungsbutton nach § 312k, AGB, Jahresverlängerung nach § 309 Nr. 9.
  - TAX: Verkäufer, USt je Land, Rechnungen.
  - ORG: wer verkauft.
  - LIC: Datenrechte.
  - FIN: KI und Alarme ohne Anlageberatung.
- **Historie:** `history.json` ist öffentlich. Soll die ganze Historie Premium sein, muss sie hinter `/api/` wandern.
- **Kündigungsbutton (§ 312k):** Er muss ohne Login erreichbar sein. Das Stripe-Portal braucht einen Login und reicht vermutlich nicht. Das kommt nach der Rechtsprüfung.
- **Doppelabo über zwei Kanäle** (z. B. Web und Apple gleichzeitig vor dem Abgleich):
  - Erkennen: RevenueCat zeigt zwei aktive Abos.
  - Lösen: das jüngere Abo beim jeweiligen Anbieter erstatten und kündigen; der Webhook setzt den Stand neu.
- **Sicherung:** `konto.db` und `alarme.db` werden noch nicht gesichert.
- **Gesperrte Nutzer:** Schaltet man `IT_PREMIUM_PFLICHT` ein, verlieren alle angemeldeten Nutzer ohne Abo sofort den aktuellen Wert, die KI und die Alarm-Mitteilungen. Vorher Bestandsnutzer informieren.
