import { writable, get } from 'svelte/store';
import type { FilterState, SortField, SortDirection } from './types';
import { readStored, writeStored } from './storage';

export type BrowsingContext =
	| {
			type: 'all';
			sort?: SortField;
			dir?: SortDirection;
			/** Set when the grid is narrowed to one source (?source_id=). */
			sourceId?: number;
			filters?: FilterState;
	  }
	| {
			type: 'collection';
			collectionId: number;
			name: string;
			filters?: FilterState;
			sort?: SortField;
			dir?: SortDirection;
	  };

const STORAGE_KEY = 'browsingContext';
const SCROLL_KEY = 'scrollPositions';

export const browsingContext = writable<BrowsingContext | null>(
	readStored<BrowsingContext | null>(STORAGE_KEY, null, 'session')
);

const scrollPositions = readStored<Record<string, number>>(SCROLL_KEY, {}, 'session');

export function setBrowsingContext(ctx: BrowsingContext): void {
	browsingContext.set(ctx);
	writeStored(STORAGE_KEY, ctx, 'session');
}

export function contextKey(ctx: BrowsingContext | null): string {
	if (!ctx) return 'none';
	if (ctx.type === 'all') return ctx.sourceId ? `source:${ctx.sourceId}` : 'all';
	return `collection:${ctx.collectionId}`;
}

export function saveScrollPosition(scrollTop: number): void {
	const ctx = get(browsingContext);
	const key = contextKey(ctx);
	scrollPositions[key] = scrollTop;
	writeStored(SCROLL_KEY, scrollPositions, 'session');
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
	writeStored(SCROLL_KEY, scrollPositions, 'session');
}

export function backDestination(ctx: BrowsingContext | null): string {
	if (!ctx) return '/';
	if (ctx.type === 'all') return ctx.sourceId ? `/?source_id=${ctx.sourceId}` : '/';
	return `/collections/${ctx.collectionId}`;
}

export function backLabel(ctx: BrowsingContext | null): string {
	if (!ctx) return '← Back';
	if (ctx.type === 'all') return '← All Images';
	return `← ${ctx.name}`;
}
