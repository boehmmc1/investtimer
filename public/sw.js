/* InvestTimer Service Worker (wird beim Build mit Versionsnummer erzeugt: tools/sw.js -> public/sw.js).
   Version: 2026.11.20-1019-f9f5965c
   - Seite (HTML) und /data/stress.json: zuerst Netz, bei Ausfall die zuletzt geladene Fassung (offline)
   - versionierte Dateien unter /media/ (Name = Inhalts-Hash): zuerst Cache
   - /api/*: nur Netz, nichts wird gespeichert (Kontodaten, KI)
   - neue Version: sofort aktiv (skipWaiting + clients.claim), alte Caches werden geloescht; die Seite laedt neu
     oder zeigt "Neue Version verfuegbar" (tools/update.js)
   - Push-Benachrichtigungen und Oeffnen der App wie bisher */
const VERSION = '2026.11.20-1019-f9f5965c';
const SEITEN = 'investtimer-seiten-' + VERSION, DATEIEN = 'investtimer-dateien-' + VERSION;
const VERSIONIERT = /^\/media\/[0-9a-f]{12}\.(woff2|ttf|svg|png|jpg)$/;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SEITEN).then(c => c.add(new Request('/', { cache: 'no-cache' }))).catch(() => {}).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(namen => Promise.all(namen.filter(n => n.startsWith('investtimer-') && n !== SEITEN && n !== DATEIEN).map(n => caches.delete(n))))
    .then(() => self.clients.claim())
    .then(() => self.clients.matchAll({ type: 'window' }))
    .then(fenster => fenster.forEach(f => f.postMessage({ typ: 'investtimer-version', version: VERSION }))));
});
self.addEventListener('message', e => {
  if (e.data && e.data.typ === 'investtimer-version?') e.source && e.source.postMessage({ typ: 'investtimer-version', version: VERSION });
});

function netzZuerst(request, schluessel) {
  return fetch(request).then(antwort => {
    if (antwort && antwort.ok && antwort.type === 'basic') {
      const kopie = antwort.clone();
      caches.open(SEITEN).then(c => c.put(schluessel || request, kopie)).catch(() => {});
    }
    return antwort;
  }).catch(() => caches.open(SEITEN).then(c => c.match(schluessel || request)).then(r => r || (request.mode === 'navigate'
    ? caches.open(SEITEN).then(c => c.match('/'))
    : Promise.reject(new Error('offline')))).then(gespeichert));
}
/* Antwort aus dem Cache kennzeichnen: die Seite zeigt dann "Offline · Stand …" */
function gespeichert(r) {
  if (!r) return r;
  const kopf = new Headers(r.headers); kopf.set('X-InvestTimer-Offline', '1');
  return r.blob().then(b => new Response(b, { status: r.status, statusText: r.statusText, headers: kopf }));
}

self.addEventListener('fetch', e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== self.location.origin) return;
  if (u.pathname.startsWith('/api/')) return;                       // nur Netz
  if (r.mode === 'navigate' && (u.pathname === '/' || u.pathname === '/index.html')) { e.respondWith(netzZuerst(r, '/')); return; }
  if (u.pathname === '/data/stress.json') { e.respondWith(netzZuerst(r, '/data/stress.json')); return; }
  if (VERSIONIERT.test(u.pathname)) {
    e.respondWith(caches.open(DATEIEN).then(c => c.match(r).then(t => t || fetch(r).then(a => { if (a.ok) c.put(r, a.clone()); return a; }))));
  }
});

self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { body: e.data ? e.data.text() : '' }; }
  const tag = d.tag || 'investtimer';
  e.waitUntil(self.registration.showNotification(d.title || 'InvestTimer', {
    body: d.body || '',
    tag,
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    lang: 'de',
    data: { url: d.url || '/' }
  }).then(() => self.clients.matchAll({ type: 'window', includeUncontrolled: true }))
    /* Empfangsbestaetigung an offene Seiten (Testnachricht: "zugestellt") */
    .then(fenster => fenster.forEach(f => f.postMessage({ typ: 'investtimer-push', tag, id: d.id || null }))));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const ziel = new URL((e.notification.data && e.notification.data.url) || '/', self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(fenster => {
    for (const f of fenster) {
      if (new URL(f.url).origin === self.location.origin && 'focus' in f) {
        f.postMessage({ typ: 'investtimer-neu-laden' });
        return f.focus();
      }
    }
    return self.clients.openWindow(ziel);
  }));
});
