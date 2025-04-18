const CACHE_NAME = 'ktu-qna-cache-v3';
const urlsToCache = [
    '/',
    '/index.html',
    '/manifest.json',
    '/ques.png',
    '/confused.png',
];

self.addEventListener('install', (event) => {
    self.skipWaiting(); 
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Service Worker: Caching files:', urlsToCache); 
                return cache.addAll(urlsToCache);
            })
    );
});

/*self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                return cachedResponse || fetch(event.request);
            })
    );
}); */ //This was my already existing below is for cache fixing
/*self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                return caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, response.clone());
                    return response;
                });
            })
            .catch(() => {
                return caches.match(event.request);
            })
    );
});
*/
self.addEventListener("fetch", event => {
    const { request } = event;

    // ✅ Ignore POST requests (don't cache them)
    if (request.method !== "GET") {
        return;
    }

    event.respondWith(
        caches.match(request).then(cachedResponse => {
            if (cachedResponse) {
                return cachedResponse;  // ✅ Return cached response if found
            }

            return fetch(request).then(response => {
                return caches.open("my-cache").then(cache => {
                    cache.put(request, response.clone());  // ✅ Cache only `GET` responses
                    return response;
                });
            });
        })
    );
});

self.addEventListener('activate', (event) => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (!cacheWhitelist.includes(cacheName)) {
                            return caches.delete(cacheName);
                        }
                    })
                );
            }).then(() => self.clients.claim())
    );
});
