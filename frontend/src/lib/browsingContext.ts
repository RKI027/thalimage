import { writable, get } from 'svelte/store';

export type BrowsingContext =
	| { type: 'all' }
	| { type: 'collection'; collectionId: number; name: string };

const STORAGE_KEY = 'browsingContext';
const SCROLL_KEY = 'scrollPositions';

function hydrate(): BrowsingContext | null {
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
}

function hydrateScrollPositions(): Record<string, number> {
	try {
		const raw = sessionStorage.getItem(SCROLL_KEY);
		return raw ? JSON.parse(raw) : {};
	} catch {
		return {};
	}
}

export const browsingContext = writable<BrowsingContext | null>(hydrate());

let scrollPositions = hydrateScrollPositions();

export function setBrowsingContext(ctx: BrowsingContext): void {
	browsingContext.set(ctx);
	sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ctx));
}

export function contextKey(ctx: BrowsingContext | null): string {
	if (!ctx) return 'none';
	if (ctx.type === 'all') return 'all';
	return `collection:${ctx.collectionId}`;
}

export function saveScrollPosition(scrollTop: number): void {
	const ctx = get(browsingContext);
	const key = contextKey(ctx);
	scrollPositions[key] = scrollTop;
	sessionStorage.setItem(SCROLL_KEY, JSON.stringify(scrollPositions));
}

export function getScrollPosition(): number {
	const ctx = get(browsingContext);
	const key = contextKey(ctx);
	return scrollPositions[key] ?? 0;
}

export function clearScrollPosition(): void {
	const ctx = get(browsingContext);
	const key = contextKey(ctx);
	delete scrollPositions[key];
	sessionStorage.setItem(SCROLL_KEY, JSON.stringify(scrollPositions));
}

export function backDestination(ctx: BrowsingContext | null): string {
	if (!ctx) return '/';
	if (ctx.type === 'all') return '/';
	return `/collections/${ctx.collectionId}`;
}

export function backLabel(ctx: BrowsingContext | null): string {
	if (!ctx) return '← Back';
	if (ctx.type === 'all') return '← All Images';
	return `← ${ctx.name}`;
}
