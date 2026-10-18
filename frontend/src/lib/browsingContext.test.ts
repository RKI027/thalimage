import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

// The module hydrates from sessionStorage at import time, so each test
// imports a fresh copy after arranging storage.
async function load() {
	vi.resetModules();
	return import('./browsingContext');
}

describe('browsingContext', () => {
	beforeEach(() => sessionStorage.clear());

	it('persists the context and restores it on the next load', async () => {
		const m = await load();
		m.setBrowsingContext({ type: 'collection', collectionId: 7, name: 'Faves', sort: 'name' });
		const again = await load();
		expect(get(again.browsingContext)).toEqual({
			type: 'collection',
			collectionId: 7,
			name: 'Faves',
			sort: 'name'
		});
	});

	it('survives corrupt storage', async () => {
		sessionStorage.setItem('browsingContext', '{not json');
		const m = await load();
		expect(get(m.browsingContext)).toBeNull();
	});

	it('keeps one scroll position per context', async () => {
		const m = await load();
		m.setBrowsingContext({ type: 'all' });
		m.saveScrollPosition(120);
		m.setBrowsingContext({ type: 'collection', collectionId: 3, name: 'c' });
		expect(m.getScrollPosition()).toBe(0);
		m.saveScrollPosition(40);
		m.setBrowsingContext({ type: 'all' });
		expect(m.getScrollPosition()).toBe(120);
		expect((await load()).getScrollPosition()).toBe(120);
	});

	it('names where Back goes', async () => {
		const m = await load();
		expect(m.backDestination(null)).toBe('/');
		expect(m.backDestination({ type: 'all' })).toBe('/');
		expect(m.backDestination({ type: 'collection', collectionId: 4, name: 'x' })).toBe(
			'/collections/4'
		);
		expect(m.backLabel({ type: 'collection', collectionId: 4, name: 'Cats' })).toBe('← Cats');
		expect(m.backLabel({ type: 'all' })).toBe('← All Images');
	});

	it('sends Back to the page that opened the viewer, when it says so', async () => {
		const m = await load();
		const ctx = {
			type: 'collection' as const,
			collectionId: 4,
			name: 'Cats',
			back: { href: '/collections/4/rankings', label: 'Rankings' }
		};
		expect(m.backDestination(ctx)).toBe('/collections/4/rankings');
		expect(m.backLabel(ctx)).toBe('← Rankings');
	});

	it('turns a context into the listing it shows (GEN-013)', async () => {
		const m = await load();
		const filters = { media_type: 'video' };
		expect(
			m.contextListing({ type: 'all', sort: 'size', sourceId: 3, filters }, true)
		).toEqual({ sort: 'size', dir: undefined, filters, show_nsfw: true, source_id: 3 });
		expect(
			m.contextListing({ type: 'collection', collectionId: 9, name: 'c', dir: 'desc' }, false)
		).toEqual({
			sort: undefined,
			dir: 'desc',
			filters: undefined,
			show_nsfw: false,
			collection_id: 9
		});
	});

	it('gives a source-filtered grid its own Back target and scroll slot', async () => {
		const m = await load();
		expect(m.backDestination({ type: 'all', sourceId: 2 })).toBe('/?source_id=2');
		expect(m.contextKey({ type: 'all', sourceId: 2 })).toBe('source:2');
	});
});

describe('groupsNearDuplicates', () => {
	it('is true for a listing grouped by near-duplicates, whatever the threshold, 0 included', async () => {
		const { groupsNearDuplicates } = await load();
		expect(groupsNearDuplicates({ type: 'all', filters: { near_duplicates: 0 } })).toBe(true);
		expect(groupsNearDuplicates({ type: 'all', filters: { near_duplicates: 0.2 } })).toBe(true);
	});

	it('is false otherwise', async () => {
		const { groupsNearDuplicates } = await load();
		expect(groupsNearDuplicates({ type: 'all', filters: {} })).toBe(false);
		expect(groupsNearDuplicates({ type: 'all' })).toBe(false);
		expect(groupsNearDuplicates(null)).toBe(false);
	});
});
