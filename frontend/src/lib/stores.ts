import { writable } from 'svelte/store';
import { listSources, listCollections } from '$lib/api';
import type { Source, Collection } from '$lib/types';

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

export const sourcesStore = createDataStore<Source>(listSources);
export const collectionsStore = createDataStore<Collection>(listCollections);
