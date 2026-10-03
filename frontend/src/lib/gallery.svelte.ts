/**
 * What the two grid pages (all images, one collection) share: paging through
 * a listing, the persisted thumbnail size, and starting a slideshow from it.
 * Each page supplies only the listing it shows.
 */
import { goto } from '$app/navigation';
import { listImages, type ListingParams } from './api';
import { responsiveThumbSize } from './mobileStore.svelte';
import { slideshowStore } from './slideshowStore.svelte';
import { readStored, writeStored } from './storage';
import type { ImageSummary } from './types';

const PAGE_SIZE = 500;
const MOBILE_MAX_WIDTH = 768;

/** Where a collection's filters are remembered (grid and ELO page alike). */
export function collectionFiltersKey(collectionId: number): string {
	return `collection:${collectionId}:filters`;
}

export class Gallery {
	images = $state<ImageSummary[]>([]);
	totalCount = $state(0);
	nextCursor = $state<string | null>(null);
	loading = $state(false);
	error = $state<string | null>(null);
	/** False until the first page (or its error) has arrived. */
	loaded = $state(false);

	#thumbSize = $state(readStored('thumbSize', 200));
	#query: () => ListingParams;
	// Each request gets a number; a response is applied only if no newer
	// request has started since, so a reset always wins over a load in flight.
	#generation = 0;
	#inFlight: AbortController | null = null;

	constructor(query: () => ListingParams) {
		this.#query = query;
	}

	get thumbSize(): number {
		return this.#thumbSize;
	}

	set thumbSize(size: number) {
		this.#thumbSize = size;
		writeStored('thumbSize', size);
	}

	/** Load the listing from its start, superseding any request in flight. */
	reset(): Promise<void> {
		return this.#fetch(null);
	}

	/** Append the next page, unless one is loading or there is none. */
	loadMore(): Promise<void> {
		if (this.loading || !this.nextCursor) return Promise.resolve();
		return this.#fetch(this.nextCursor);
	}

	async #fetch(cursor: string | null): Promise<void> {
		this.#inFlight?.abort();
		const generation = ++this.#generation;
		const controller = new AbortController();
		this.#inFlight = controller;
		this.loading = true;
		this.error = null;
		try {
			const pg = await listImages(
				{ ...this.#query(), cursor, limit: PAGE_SIZE },
				{ signal: controller.signal }
			);
			if (generation !== this.#generation) return;
			this.images = cursor === null ? pg.items : [...this.images, ...pg.items];
			this.totalCount = pg.total_count;
			this.nextCursor = pg.next_cursor;
		} catch (e) {
			if (generation !== this.#generation) return;
			this.error = e instanceof Error ? e.message : 'Failed to load images';
		} finally {
			if (generation === this.#generation) {
				this.loading = false;
				this.loaded = true;
				this.#inFlight = null;
			}
		}
	}

	startSlideshow(): void {
		if (this.images.length === 0) return;
		slideshowStore.scheduleStart();
		goto(`/image/${this.images[0].content_hash}`);
	}

	/** On phones, size thumbnails to the viewport. Returns the cleanup. */
	followViewport(): () => void {
		const update = () => {
			if (window.innerWidth <= MOBILE_MAX_WIDTH) this.thumbSize = responsiveThumbSize();
		};
		update();
		window.addEventListener('resize', update);
		return () => window.removeEventListener('resize', update);
	}
}
