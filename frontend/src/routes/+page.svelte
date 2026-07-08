<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { goto } from '$app/navigation';
	import { listImages } from '$lib/api';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import { settingsStore } from '$lib/stores';
	import type { ImageSummary, SortField, SortDirection } from '$lib/types';
	import { responsiveThumbSize } from '$lib/mobileStore.svelte';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import GridToolbar from '$lib/components/GridToolbar.svelte';
	import type { FilterState } from '$lib/types';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let filters: FilterState = $state({});
	let sourceId: number | undefined = $state(undefined);
	let thumbSize = $state(Number(localStorage.getItem('thumbSize')) || 200);
	let loading = $state(false);
	let error: string | null = $state(null);
	let initialLoad = $state(true);
	let currentScrollTop = $state(0);
	let restoredScrollTop = $state(0);
	$effect(() => { localStorage.setItem('thumbSize', String(thumbSize)); });

	beforeNavigate(() => {
		saveScrollPosition(currentScrollTop);
	});

	async function fetchImages(reset = false) {
		if (loading) return;
		loading = true;
		error = null;
		try {
			const pg = await listImages({
				cursor: reset ? undefined : (nextCursor ?? undefined),
				limit: 500,
				sort,
				dir,
				source_id: sourceId,
				filters,
				show_nsfw: $settingsStore.show_nsfw
			});
			if (reset) {
				images = pg.items;
			} else {
				images = [...images, ...pg.items];
			}
			totalCount = pg.total_count;
			nextCursor = pg.next_cursor;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load images';
		} finally {
			loading = false;
			initialLoad = false;
		}
	}

	function startSlideshow() {
		if (images.length === 0) return;
		slideshowStore.scheduleStart();
		goto(`/image/${images[0].content_hash}`);
	}

	function galleryKey(key: string): string {
		return `gallery:${sourceId ?? 'all'}:${key}`;
	}

	function loadPrefs() {
		sort = (localStorage.getItem(galleryKey('sort')) as SortField) || 'name';
		dir = (localStorage.getItem(galleryKey('dir')) as SortDirection) || 'asc';
		filters = JSON.parse(localStorage.getItem(galleryKey('filters')) ?? '{}');
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		localStorage.setItem(galleryKey('sort'), newSort);
		localStorage.setItem(galleryKey('dir'), newDir);
		setBrowsingContext({ type: 'all', sort, dir });
		fetchImages(true);
	}

	function onFilterChange(newFilters: FilterState) {
		filters = newFilters;
		localStorage.setItem(galleryKey('filters'), JSON.stringify(newFilters));
		fetchImages(true);
	}

	function readSourceId(): number | undefined {
		const v = $page.url.searchParams.get('source_id');
		return v ? Number(v) : undefined;
	}

	onMount(() => {
		restoredScrollTop = getScrollPosition();
		sourceId = readSourceId();
		loadPrefs();
		setBrowsingContext({ type: 'all', sort, dir });
		fetchImages(true);

		// Set responsive thumb size on mobile
		function updateThumbSize() {
			if (window.innerWidth <= 768) {
				thumbSize = responsiveThumbSize();
			}
		}
		updateThumbSize();
		window.addEventListener('resize', updateThumbSize);
		return () => window.removeEventListener('resize', updateThumbSize);
	});

	// Re-fetch when source_id query param changes
	$effect(() => {
		const newId = readSourceId();
		untrack(() => {
			if (newId !== sourceId) {
				sourceId = newId;
				loadPrefs();
				fetchImages(true);
			}
		});
	});

	// Re-fetch when show_nsfw setting changes (skip during initial load)
	$effect(() => {
		const _ = $settingsStore.show_nsfw;
		untrack(() => { if (!initialLoad) fetchImages(true); });
	});

</script>

{#if error}
	<div class="status error">{error}</div>
{:else if initialLoad}
	<div class="status">Loading…</div>
{:else if totalCount === 0}
	<div class="status empty">
		<p>No images found.</p>
		<p>Add a source folder in <a href="/settings?returnTo=/">Settings</a> and trigger a scan.</p>
	</div>
{:else}
	<GridToolbar
		{sort}
		{dir}
		{filters}
		bind:thumbSize
		count={totalCount}
		{loading}
		disabled={images.length === 0}
		title="All Images"
		leftType="hamburger"
		{onSortChange}
		{onFilterChange}
		onStartSlideshow={startSlideshow}
	/>

	<ImageGrid
		{images}
		{totalCount}
		thumbSize={thumbSize}
		initialScrollTop={restoredScrollTop}
		onLoadMore={() => nextCursor && fetchImages()}
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
