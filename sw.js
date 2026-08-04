// Service Worker – Network-first für die App-Shell, damit Updates sofort ankommen.
// Cache dient nur als Offline-Fallback. Version bei jedem Update hochzählen.
const CACHE = "pwmgr-v3";
const ASSETS = ["./","./index.html","./manifest.webmanifest","./icon-192.png","./icon-512.png"];

self.addEventListener("install", (e)=>{
  self.skipWaiting(); // neuen SW sofort aktiv werden lassen
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).catch(()=>{}));
});

self.addEventListener("activate", (e)=>{
  e.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener("message",(e)=>{ if(e.data==="skipWaiting") self.skipWaiting(); });

self.addEventListener("fetch", (e)=>{
  if(e.request.method!=="GET") return;
  const url=new URL(e.request.url);
  const isShell = url.pathname.endsWith("/") || url.pathname.endsWith("/index.html")
                || url.pathname.endsWith("index.html");
  if(isShell){
    // Network-first: immer versuchen, die neueste index.html zu holen
    e.respondWith(
      fetch(e.request).then(res=>{
        const copy=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,copy)).catch(()=>{});
        return res;
      }).catch(()=>caches.match(e.request).then(hit=>hit||caches.match("./index.html")))
    );
  } else {
    // Übrige Assets: cache-first (schnell, offline)
    e.respondWith(
      caches.match(e.request).then(hit=> hit || fetch(e.request).then(res=>{
        const copy=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,copy)).catch(()=>{});
        return res;
      }).catch(()=>caches.match("./index.html")))
    );
  }
});
