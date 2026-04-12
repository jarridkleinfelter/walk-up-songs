// Service Worker — KML Chargers Walk-Up Songs
// CACHE version is replaced with a UTC timestamp by the GitHub Actions
// deploy workflow on every push. Format: walkup-YYYYMMDDTHHMMSSZ
// Do not edit this line manually — the sed pattern matches it exactly.
const CACHE = 'walkup-v1';
const ASSETS = ['/index.html', '/'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
