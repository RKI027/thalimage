import { writable } from 'svelte/store';
import { listSources, listCollections, getSettings, patchSettings } from '$lib/api';
import type { Source, Collection, UserSettings } from '$lib/types';

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
	const { subscribe, set } = writable<UserSettings>({ show_nsfw: false });

	async function refresh() {
		set(await getSettings());
	}

	async function patch(updates: Partial<UserSettings>) {
		set(await patchSettings(updates));
	}

	return { subscribe, refresh, patch };
}

export const sourcesStore = createDataStore<Source>(listSources);
export const collectionsStore = createDataStore<Collection>(listCollections);
export const settingsStore = createSettingsStore();
