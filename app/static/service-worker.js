const CACHE_NAME = 'valifood-v2';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/scanner.js',
    '/static/js/products.js',
    '/static/js/notifications.js',
    '/static/icons/icon-192x192.png'
];

self.addEventListener('install', e => {
    e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)));
    self.skipWaiting();
});

self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(names =>
            Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', e => {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        caches.match(e.request).then(cached => {
            if (cached) return cached;
            return fetch(e.request).catch(() => {
                if (e.request.mode === 'navigate') return caches.match('/');
            });
        })
    );
});

// ===== Notificações Push =====
self.addEventListener('push', e => {
    let data = { title: 'ValiFood', body: 'Você tem alertas de vencimento.', url: '/', tag: 'valifood' };
    if (e.data) {
        try { data = Object.assign(data, e.data.json()); } catch (err) { data.body = e.data.text(); }
    }
    e.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-192x192.png',
            tag: data.tag,
            renotify: true,
            data: { url: data.url },
            vibrate: [200, 100, 200]
        })
    );
});

self.addEventListener('notificationclick', e => {
    e.notification.close();
    const url = (e.notification.data && e.notification.data.url) || '/';
    e.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
            for (const client of windowClients) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});
