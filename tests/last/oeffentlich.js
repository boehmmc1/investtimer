// Lasttest oeffentliche Seiten (k6). Aufruf: k6 run -e STUFE=50 tests/last/oeffentlich.js
// Jeder virtuelle Besucher: Startseite, stress.json, Teilen-Manifest; jeder dritte zusaetzlich Verlauf und ein Teilen-Bild. Denkpause 2-5 s.
import http from 'k6/http';
import { check, sleep } from 'k6';
const SEITE = __ENV.SEITE || 'https://investtimer.net';
const N = parseInt(__ENV.STUFE || '50');
export const options = {
  scenarios: { last: { executor: 'ramping-vus', startVUs: 0, stages: [{ duration: '20s', target: N }, { duration: '60s', target: N }, { duration: '10s', target: 0 }] } },
  thresholds: { http_req_failed: [{ threshold: 'rate<0.02', abortOnFail: true, delayAbortEval: '15s' }] },
  summaryTrendStats: ['med', 'p(95)', 'max'],
};
export default function () {
  const kopf = { headers: { 'Accept-Encoding': 'gzip', 'User-Agent': 'investtimer-lasttest' } };
  let r = http.get(SEITE + '/', kopf); check(r, { 'start 200': (x) => x.status === 200 });
  r = http.get(SEITE + '/data/stress.json', kopf); check(r, { 'stress 200': (x) => x.status === 200 });
  r = http.get(SEITE + '/teilen/aktuell/manifest.json', kopf); check(r, { 'manifest 200': (x) => x.status === 200 });
  if (__ITER % 3 === 0) {
    r = http.get(SEITE + '/api/historie-oeffentlich', kopf); check(r, { 'verlauf 200': (x) => x.status === 200 });
    r = http.get(SEITE + '/api/teilen/bild?art=verlauf&zeitraum=1J&format=quer&l=de', Object.assign({ redirects: 1 }, kopf)); check(r, { 'bild 200': (x) => x.status === 200 });
  }
  sleep(2 + Math.random() * 3);
}
