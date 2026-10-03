<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import { Gallery } from '$lib/gallery.svelte';
	import { readStored, writeStored } from '$lib/storage';
	import { settingsStore } from '$lib/stores';
	import type { FilterState, SortField, SortDirection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import GridToolbar from '$lib/components/GridToolbar.svelte';

	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let filters: FilterState = $state({});
	let sourceId: number | undefined = $state(undefined);
	let currentScrollTop = $state(0);
	let restoredScrollTop = $state(0);

	const gallery = new Gallery(() => ({
		sort,
		dir,
		source_id: sourceId,
		filters,
		show_nsfw: $settingsStore.show_nsfw
	}));

	beforeNavigate(() => {
		saveScrollPosition(currentScrollTop);
	});

	function galleryKey(key: string): string {
		return `gallery:${sourceId ?? 'all'}:${key}`;
	}

	function loadPrefs() {
		sort = readStored<SortField>(galleryKey('sort'), 'name');
		dir = readStored<SortDirection>(galleryKey('dir'), 'asc');
		filters = readStored<FilterState>(galleryKey('filters'), {});
	}

	// The viewer walks prev/next through exactly this listing.
	function rememberContext() {
		setBrowsingContext({ type: 'all', sort, dir, sourceId, filters });
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		writeStored(galleryKey('sort'), newSort);
		writeStored(galleryKey('dir'), newDir);
		rememberContext();
		gallery.reset();
	}

	function onFilterChange(newFilters: FilterState) {
		filters = newFilters;
		writeStored(galleryKey('filters'), newFilters);
		rememberContext();
		gallery.reset();
	}

	function readSourceId(): number | undefined {
		const v = $page.url.searchParams.get('source_id');
		return v ? Number(v) : undefined;
	}

	onMount(() => {
		restoredScrollTop = getScrollPosition();
		sourceId = readSourceId();
		loadPrefs();
		rememberContext();
		gallery.reset();
		return gallery.followViewport();
	});

	// Re-fetch when source_id query param changes
	$effect(() => {
		const newId = readSourceId();
		untrack(() => {
			if (newId !== sourceId) {
				sourceId = newId;
				loadPrefs();
				rememberContext();
				gallery.reset();
			}
		});
	});

	// Re-fetch when show_nsfw setting changes (skip during initial load)
	$effect(() => {
		const _ = $settingsStore.show_nsfw;
		untrack(() => { if (gallery.loaded) gallery.reset(); });
	});

</script>

{#if gallery.error}
	<div class="status error">{gallery.error}</div>
{:else if !gallery.loaded}
	<div class="status">Loading…</div>
{:else if gallery.totalCount === 0}
	<div class="status empty">
		<p>No images found.</p>
		<p>Add a source folder in <a href="/settings?returnTo=/">Settings</a> and trigger a scan.</p>
	</div>
{:else}
	<GridToolbar
		{sort}
		{dir}
		{filters}
		bind:thumbSize={gallery.thumbSize}
		count={gallery.totalCount}
		loading={gallery.loading}
		disabled={gallery.images.length === 0}
		title="All Images"
		leftType="hamburger"
		{onSortChange}
		{onFilterChange}
		onStartSlideshow={() => gallery.startSlideshow()}
	/>

	<ImageGrid
		images={gallery.images}
		totalCount={gallery.totalCount}
		thumbSize={gallery.thumbSize}
		initialScrollTop={restoredScrollTop}
		onLoadMore={() => gallery.loadMore()}
		onScroll={(s) => { currentScrollTop = s; }}
	/>
{/if}

<style>
	.status {
		padding: 48px 24px;
		text-align: center;
		color: #888;
	}

	.status.error {
		color: #f66;
	}

	.status.empty p {
		margin: 4px 0;
	}
</style>
