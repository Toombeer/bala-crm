const CACHE = 'bala-app-v3';
const FILES = ['./', 'index.html', 'app.js?v=3', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))); self.clients.claim(); });
const fresh = req => fetch(req).then(r => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return r; });
self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  if (req.mode === 'navigate') { e.respondWith(fresh(req).catch(() => caches.match('index.html'))); return; }
  if (url.pathname.endsWith('rates.json') || url.pathname.endsWith('app.js')) { e.respondWith(fresh(req).catch(() => caches.match(req))); return; }
  e.respondWith(caches.match(req).then(hit => hit || fresh(req)));
});
