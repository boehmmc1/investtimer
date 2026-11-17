// Baut den Web-Inhalt der App (www/) aus der fertigen Website (../public).
// Eine Codebasis: dieselbe index.html wie im Web, ergaenzt um app-bruecke.js
// (API-Adresse, native Push-Mitteilungen, Kauf ueber Apple/RevenueCat).
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
const ZIEL = "www", QUELLE = "../public";
const konfig = existsSync("app.json") ? JSON.parse(readFileSync("app.json", "utf8")) : {};
rmSync(ZIEL, { recursive: true, force: true });
mkdirSync(ZIEL, { recursive: true });
for (const d of ["index.html", "impressum.html", "datenschutz.html", "agb.html", "manifest.json", "icon-192.png", "icon-512.png",
                 "apple-touch-icon.png", "og-image.png", "film"]) {
  if (existsSync(`${QUELLE}/${d}`)) cpSync(`${QUELLE}/${d}`, `${ZIEL}/${d}`, { recursive: true });
}
cpSync("app-bruecke.js", `${ZIEL}/app-bruecke.js`);
let html = readFileSync(`${ZIEL}/index.html`, "utf8");
const einstellungen = { api: konfig.api || "https://investtimer.net", revenuecatApple: konfig.revenuecatApple || "",
  revenuecatGoogle: konfig.revenuecatGoogle || "", fcm: !!konfig.fcm };
const kopf = `<script>window.INVESTTIMER_APP=${JSON.stringify(einstellungen)};</script><script src="app-bruecke.js"></script>`;
if (!html.includes("<head>")) throw new Error("kein <head> in index.html");
html = html.replace("<head>", "<head>" + kopf);
// CSP der Website um die App-Quellen erweitern (API-Domain, Capacitor-Bruecke)
html = html.replace(/connect-src ([^;"]*)/, (m, q) => `connect-src ${q} ${einstellungen.api} https://api.revenuecat.com`);
html = html.replace(/script-src ([^;"]*)/, (m, q) => q.includes("'self'") ? m : `script-src 'self' ${q}`);
writeFileSync(`${ZIEL}/index.html`, html);
console.log("www gebaut:", Object.keys(einstellungen).map(k => `${k}=${einstellungen[k] ? "gesetzt" : "leer"}`).join(", "));
