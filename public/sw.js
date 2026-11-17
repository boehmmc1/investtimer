/* InvestTimer Service Worker: nur Push-Benachrichtigungen und das Oeffnen der App.
   Kein Zwischenspeichern von Seiten oder Daten, damit nie ein veralteter Wert erscheint. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'InvestTimer', {
    body: d.body || '',
    tag: d.tag || 'investtimer',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    lang: 'de',
    data: { url: d.url || '/' }
  }));
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
