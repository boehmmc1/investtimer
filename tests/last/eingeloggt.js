// Lasttest eingeloggt (k6): /api/aktuell und Verlauf mit echten Test-Tokens (TOKENS = durch Komma getrennt).
import http from 'k6/http';
import { check, sleep } from 'k6';
const SEITE = __ENV.SEITE || 'https://investtimer.net';
const TOKENS = (__ENV.TOKENS || '').split(',');
const N = parseInt(__ENV.STUFE || '100');
export const options = {
  scenarios: { last: { executor: 'ramping-vus', startVUs: 0, stages: [{ duration: '20s', target: N }, { duration: '60s', target: N }, { duration: '10s', target: 0 }] } },
  thresholds: { http_req_failed: [{ threshold: 'rate<0.02', abortOnFail: true, delayAbortEval: '15s' }] },
  summaryTrendStats: ['med', 'p(95)', 'max'],
};
export default function () {
  const t = TOKENS[(__VU - 1) % TOKENS.length];
  const kopf = { headers: { Authorization: 'Bearer ' + t, 'Accept-Encoding': 'gzip', 'User-Agent': 'investtimer-lasttest' } };
  let r = http.get(SEITE + '/api/aktuell', kopf); check(r, { 'aktuell 200': (x) => x.status === 200 });
  if (__ITER % 4 === 0) { r = http.get(SEITE + '/api/historie', kopf); check(r, { 'historie 200': (x) => x.status === 200 }); }
  sleep(3 + Math.random() * 4);
}
