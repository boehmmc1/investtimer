# iOS-App bauen und veröffentlichen

Die App ist ein Capacitor-8-Projekt in `app/`. Sie zeigt dieselbe `public/index.html` wie die Website. Dazu kommt `app/app-bruecke.js`:
- leitet relative `/api`- und `/data`-Aufrufe an `https://investtimer.net`;
- schaltet native Push-Mitteilungen über APNs ein;
- wickelt den Apple-Kauf über RevenueCat ab.

Die Schnittstellen der Website erlauben dafür die Herkunft `capacitor://localhost` (CORS in nginx).

## Kennzahlen

| | |
|---|---|
| Name | InvestTimer |
| Bundle-ID | `net.investtimer.app` |
| Geräte | iPhone (ab iOS 15) |
| Abos | `net.investtimer.premium.monthly`, `net.investtimer.premium.yearly`, Berechtigung `premium` |
| Push | APNs, Entitlement `aps-environment` (beim Export für den App Store automatisch `production`) |

## Inhalt aktualisieren (ohne Mac)

```bash
cd app
PATH=/opt/node22/bin:$PATH node bauen.mjs     # www/ aus ../public bauen
PATH=/opt/node22/bin:$PATH npx cap sync ios   # nach ios/App/App/public kopieren
```

Ein Push nach `main`, der `app/`, `public/index.html`, `tools/konto.js` oder `tools/alarme.js` ändert, startet `.github/workflows/ios.yml`. Der Workflow baut die App auf einem macOS-Rechner von GitHub für den Simulator, ohne Signatur. Das zeigt, dass Projekt und Plugins kompilieren.

## Signierter Build und TestFlight (braucht das Apple-Entwicklerkonto)

1. Unter developer.apple.com die App-ID `net.investtimer.app` mit „Push Notifications“ anlegen.
2. In App Store Connect die App anlegen. Primärsprache Deutsch, Kategorie Finanzen.
   - Abos und Einführungsangebot einrichten (siehe `docs/premium-und-app.md`).
   - Datenschutzangaben eintragen: E-Mail, Nutzer-ID, Kaufhistorie und Inhalte (KI-Fragen), jeweils verknüpft und ohne Tracking.
3. Bauen, Weg A, mit einem Mac:
   - `cd app && npm ci && node bauen.mjs && npx cap open ios`;
   - in Xcode das Team wählen, dann Product → Archive → Distribute → App Store Connect.
4. Bauen, Weg B, ohne Mac über GitHub Actions. Dafür müssen diese Secrets im Repository hinterlegt sein:
   - App-Store-Connect-API-Schlüssel (`.p8`, Key-ID, Issuer-ID);
   - Signaturzertifikat (`.p12` mit Passwort);
   - Provisioning-Profil.

   Der Workflow archiviert dann mit `xcodebuild archive` und lädt den Build mit `xcrun altool` hoch. Er wird ergänzt, sobald die Schlüssel da sind.
5. In TestFlight intern testen:
   - Anmeldung mit Code;
   - Push erlauben, Testnachricht senden;
   - Testkauf mit einem Sandbox-Konto;
   - Käufe wiederherstellen;
   - Konto löschen.
6. Zur Prüfung einreichen. Für den App-Review:
   - ein Demo-Konto mit Anmeldecode;
   - der Hinweis, dass die Inhalte ohne Anlageberatung sind;
   - die Kontolöschung, zu finden unter „Mein Konto“ → „Konto löschen“.

## Server

- **APNs-Schlüssel:** `/root/.investtimer/apns.json` (0600) mit `{"p8": "/root/.investtimer/apns-KEYID.p8", "key_id": "...", "team_id": "...", "bundle": "net.investtimer.app", "sandbox": false}`.
  - Für TestFlight und App-Store-Builds gilt `sandbox: false`, für Xcode-Debug-Builds `true`.
- **Versand:** `server/push_senden.py` schickt Web-Push und APNs gemeinsam. Geräte mit dem Token `apns:<hex>` gehen über HTTP/2 an Apple (httpx in `/opt/investtimer-push`).
