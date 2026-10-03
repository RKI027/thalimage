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
});
