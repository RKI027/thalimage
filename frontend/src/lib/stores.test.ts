import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api', () => ({
	listCollections: vi.fn(),
	getSettings: vi.fn(),
	patchSettings: vi.fn()
}));

import { getSettings } from '$lib/api';

beforeEach(() => {
	vi.resetModules();
	vi.mocked(getSettings).mockReset();
});

async function freshSettingsStore() {
	return (await import('./stores')).settingsStore;
}

describe('settingsStore.loaded', () => {
	it('stays pending until the settings have been fetched', async () => {
		const store = await freshSettingsStore();
		let settled = false;
		store.loaded.then(() => (settled = true));
		await Promise.resolve();
		expect(settled).toBe(false);
	});

	it('resolves once the server settings are in the store', async () => {
		vi.mocked(getSettings).mockResolvedValue({ show_nsfw: true, edit_threshold: 0.25 });
		const store = await freshSettingsStore();
		store.refresh();
		await store.loaded;
		expect(get(store).show_nsfw).toBe(true);
	});

	it('resolves on the defaults when fetching the settings fails', async () => {
		vi.mocked(getSettings).mockRejectedValue(new Error('offline'));
		const store = await freshSettingsStore();
		await store.refresh().catch(() => {});
		await store.loaded;
		expect(get(store).show_nsfw).toBe(false);
	});
});
