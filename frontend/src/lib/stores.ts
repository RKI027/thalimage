import { writable } from 'svelte/store';
import { listCollections, getSettings, patchSettings } from '$lib/api';
import type { Collection, UserSettings } from '$lib/types';

function createDataStore<T>(fetcher: () => Promise<T[]>) {
	const { subscribe, set } = writable<T[]>([]);
	let loading = false;

	async function refresh() {
		if (loading) return;
		loading = true;
		try {
			set(await fetcher());
		} finally {
			loading = false;
		}
	}

	return { subscribe, refresh };
}

function createSettingsStore() {
	const { subscribe, set } = writable<UserSettings>({ show_nsfw: false, edit_threshold: 0.25 });

	// Settles after the first refresh, failed or not, so a page can hold its
	// first fetch until the server's settings (not the defaults) are known.
	let markLoaded: () => void;
	const loaded = new Promise<void>((resolve) => (markLoaded = resolve));

	async function refresh() {
		try {
			set(await getSettings());
		} finally {
			markLoaded();
		}
	}

	async function patch(updates: Partial<UserSettings>) {
		set(await patchSettings(updates));
	}

	return { subscribe, refresh, patch, loaded };
}

export const collectionsStore = createDataStore<Collection>(listCollections);
export const settingsStore = createSettingsStore();
