# Entwürfe Abo-Rechtstexte – NICHT veröffentlichen

Stand 17.11.2026. Diese Texte sind Arbeitsentwürfe von Claude, keine Rechtsberatung.
Sie werden erst nach Prüfung (Prüfpartner, dann Anwalt für IT-/Verbraucherrecht) und Klärung
von ORG-001/TAX-001/TAX-002 veröffentlicht. Offene Stellen sind mit **[PRÜFEN: …]** markiert.

| Datei | Zweck | Wird zu |
|---|---|---|
| `abo-bedingungen.md` | Vertragsbedingungen für InvestTimer Premium (Web) | `public/agb.html` (Link in Paywall und Stripe-Portal) |
| `widerrufsbelehrung.md` | Widerrufsbelehrung + Muster-Widerrufsformular | Abschnitt in `agb.html`, Text in der Bestätigungsmail |
| `datenschutz-abo.md` | Ergänzungen der Datenschutzerklärung für Stripe, RevenueCat, Apple, Abo-Mails | neue Abschnitte in `datenschutz.body.html` |

## Wichtigste Prüffragen (Kurzfassung)

1. **Jahresabo und § 309 Nr. 9 BGB:** Nach der ersten Laufzeit darf sich ein Verbrauchervertrag per AGB nur auf
   unbestimmte Zeit mit höchstens einem Monat Kündigungsfrist verlängern. Ein Web-Jahresabo „verlängert sich um ein
   weiteres Jahr“ wäre danach unwirksam. Technisch vorbereitet: Schalter `verlaengerung_monatlich` in `stripe.json`
   (Kündigung eines verlängerten Jahresabos wirkt nach spätestens einem Monat, Rest wird anteilig erstattet – Erstattung derzeit von Hand).
   Alternative: Jahresabo ohne automatische Verlängerung oder Verlängerung nur in ein Monatsabo. **Entscheidung nach Anwaltsprüfung.**
2. **Widerruf und Testphase:** Beginn der Widerrufsfrist bei Vertragsschluss (Teststart), Wertersatz nach § 357a BGB
   bei Widerruf nach Beginn der Leistung, Ausdrückliches Verlangen des Leistungsbeginns im Checkout nötig?
3. **Bestellknopf (§ 312j BGB):** Der Bezahlknopf liegt bei Stripe Checkout („Abonnieren“/„Testphase starten“).
   Reicht diese Beschriftung, oder braucht es einen eigenen Bestellschritt mit „zahlungspflichtig bestellen“ bzw.
   „kostenlos testen, danach zahlungspflichtig“? 
4. **Kündigungsbutton (§ 312k BGB) / Widerrufsbutton (§ 356a BGB):** Umsetzung unter `/vertrag-kuendigen.html`
   und `/vertrag-widerrufen.html` gegen den Gesetzestext und die aktuelle Rechtsprechung (BGH) prüfen,
   insbesondere Beschriftungen, Pflichtfelder und Bestätigung.
5. **Wer ist Verkäufer** (ORG-001, TAX-002): Davon hängen Anbieterangaben, Steuerhinweis „inkl. USt.“ bzw.
   Kleinunternehmerhinweis und die Rechnungsstellung ab.
