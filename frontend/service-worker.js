const CACHE_NAME = 'clube-do-ingles-v2';
const ASSETS = ['/', '/index.html', '/css/app.css', '/js/api.js', '/js/app.js', '/manifest.json', '/assets/logo.svg'];
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.map(k => k !== CACHE_NAME ? caches.delete(k) : null))));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/') || url.port === '8008') return;
  event.respondWith(caches.match(event.request).then(res => res || fetch(event.request).catch(() => caches.match('/index.html'))));
});
