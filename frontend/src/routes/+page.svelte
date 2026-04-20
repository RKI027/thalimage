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
	import SortControls from '$lib/components/SortControls.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import ThumbSizeSlider from '$lib/components/ThumbSizeSlider.svelte';
	import MobilePageHeader from '$lib/components/MobilePageHeader.svelte';
	import OptionsSheet from '$lib/components/OptionsSheet.svelte';
	import type { FilterState } from '$lib/types';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let filters: FilterState = $state({});
	let sourceId: number | undefined = $state(undefined);
	let thumbSize = $state(Number(localStorage.getItem('thumbSize')) || 200);
	let filtersOpen = $state(true);
	let optionsOpen = $state(false);
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
		setBrowsingContext({ type: 'all' });
		restoredScrollTop = getScrollPosition();
		sourceId = readSourceId();
		loadPrefs();
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
	<!-- Mobile single-row header -->
	<div class="mobile-only">
		<MobilePageHeader
			leftType="hamburger"
			title="All Images"
			onMenuOpen={() => (optionsOpen = true)}
		/>
	</div>

	<!-- Desktop toolbar -->
	<div class="toolbar desktop-only">
		<button class="collapse-btn" onclick={() => (filtersOpen = !filtersOpen)} title="Toggle sort controls">⊟</button>
		{#if filtersOpen}
			<div class="filter-row">
				<SortControls {sort} {dir} onchange={onSortChange} />
				<FilterBar {filters} onchange={onFilterChange} />
				<ThumbSizeSlider bind:size={thumbSize} />
			</div>
		{/if}
		<button class="slideshow-btn" onclick={startSlideshow} disabled={images.length === 0}>▶ Slideshow</button>
		<span class="count">
			{totalCount} images
			{#if loading}<span class="loading-hint"> (loading…)</span>{/if}
		</span>
	</div>

	<ImageGrid
		{images}
		{totalCount}
		thumbSize={thumbSize}
		initialScrollTop={restoredScrollTop}
		onLoadMore={() => nextCursor && fetchImages()}
		onScroll={(s) => { currentScrollTop = s; }}
	/>

	<!-- Mobile options sheet -->
	<OptionsSheet open={optionsOpen} onclose={() => (optionsOpen = false)}>
		<div class="sheet-count">{totalCount} images{#if loading} (loading…){/if}</div>
		<h3 class="sheet-section">Sort by</h3>
		<SortControls {sort} {dir} onchange={(s, d) => { onSortChange(s, d); optionsOpen = false; }} />
		<h3 class="sheet-section">Filter</h3>
		<FilterBar {filters} onchange={(f) => { onFilterChange(f); }} />
		<h3 class="sheet-section">Thumbnail size</h3>
		<ThumbSizeSlider bind:size={thumbSize} />
		<h3 class="sheet-section">Actions</h3>
		<button class="sheet-action-btn" onclick={() => { startSlideshow(); optionsOpen = false; }} disabled={images.length === 0}>▶ Slideshow</button>
	</OptionsSheet>
{/if}

<style>
	.toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 0 8px;
		flex-shrink: 0;
	}

	.collapse-btn {
		background: none;
		border: 1px solid #444;
		border-radius: 4px;
		color: #888;
		cursor: pointer;
		font-size: 1rem;
		padding: 4px 8px;
		flex-shrink: 0;
	}

	.filter-row {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
	}

	.count {
		color: #888;
		font-size: 0.85rem;
		padding-right: 8px;
		margin-left: auto;
	}

	.slideshow-btn {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
		font-size: 0.85rem;
		flex-shrink: 0;
	}

	.slideshow-btn:hover:not(:disabled) {
		background: #3a3a3a;
	}

	.slideshow-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.sheet-action-btn {
		display: block;
		padding: 12px 0;
		color: #6ea8fe;
		font-size: 0.95rem;
		background: none;
		border: none;
		cursor: pointer;
		text-align: left;
	}

	.sheet-action-btn:hover:not(:disabled) {
		color: #90c0ff;
	}

	.sheet-action-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}

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

	.loading-hint {
		color: #666;
	}

	/* Mobile/desktop visibility */
	.mobile-only { display: none; }
	.desktop-only { display: flex; }

	.sheet-count {
		color: #888;
		font-size: 0.85rem;
		margin-bottom: 16px;
	}

	.sheet-section {
		margin: 16px 0 8px;
		font-size: 0.8rem;
		color: #6ea8fe;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.sheet-section:first-of-type {
		margin-top: 0;
	}

	@media (max-width: 768px) {
		.mobile-only { display: block; }
		.desktop-only { display: none; }
	}
</style>
