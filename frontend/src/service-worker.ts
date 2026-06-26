/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE = `thalimage-${version}`;

// Built client assets (hashed, immutable) plus static files (icons, manifest).
const ASSETS = [...build, ...files];

sw.addEventListener('install', (event) => {
	async function precache() {
		const cache = await caches.open(CACHE);
		await cache.addAll(ASSETS);
	}
	event.waitUntil(precache().then(() => sw.skipWaiting()));
});

sw.addEventListener('activate', (event) => {
	async function cleanup() {
		for (const key of await caches.keys()) {
			if (key !== CACHE) await caches.delete(key);
		}
		await sw.clients.claim();
	}
	event.waitUntil(cleanup());
});

sw.addEventListener('fetch', (event) => {
	if (event.request.method !== 'GET') return;

	const url = new URL(event.request.url);

	// Let the browser handle cross-origin requests untouched.
	if (url.origin !== sw.location.origin) return;
	// Never cache API data — always hit the network.
	if (url.pathname.startsWith('/api')) return;

	async function respond() {
		const cache = await caches.open(CACHE);

		// Precached build/static assets: serve from cache.
		if (ASSETS.includes(url.pathname)) {
			const cached = await cache.match(url.pathname);
			if (cached) return cached;
		}

		// App-shell navigations: network-first, falling back to the cached
		// shell so cold and offline launches still render the SPA.
		if (event.request.mode === 'navigate') {
			try {
				const response = await fetch(event.request);
				if (response.status === 200) cache.put('/', response.clone());
				return response;
			} catch (err) {
				const cached = await cache.match('/');
				if (cached) return cached;
				throw err;
			}
		}

		// Everything else (thumbnails, image files): network, not cached.
		return fetch(event.request);
	}

	event.respondWith(respond());
});
