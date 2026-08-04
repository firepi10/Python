/* Bayta service worker — app-shell caching only.
   API and media requests always hit the network (the backend is the source
   of truth and the SSE stream keeps data fresh); hashed build assets are
   cached forever; navigations fall back to the cached shell offline. */

const SHELL_CACHE = "bayta-shell-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(["/", "/manifest.webmanifest"])),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/media/")) return;

  // hashed assets: cache-first
  if (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(event.request).then(
        (hit) =>
          hit ||
          fetch(event.request).then((resp) => {
            const copy = resp.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy));
            return resp;
          }),
      ),
    );
    return;
  }

  // navigations: network-first with cached shell fallback
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put("/", copy));
          return resp;
        })
        .catch(() => caches.match("/")),
    );
  }
});
