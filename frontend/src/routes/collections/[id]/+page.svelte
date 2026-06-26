<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto, beforeNavigate } from '$app/navigation';
	import { listImages, getCollection as fetchCollection, updateCollection } from '$lib/api';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import { settingsStore } from '$lib/stores';
	import type { ImageSummary, Collection } from '$lib/types';
	import { responsiveThumbSize } from '$lib/mobileStore.svelte';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import ThumbSizeSlider from '$lib/components/ThumbSizeSlider.svelte';
	import MobilePageHeader from '$lib/components/MobilePageHeader.svelte';
	import OptionsSheet from '$lib/components/OptionsSheet.svelte';
	import type { FilterState, SortField, SortDirection } from '$lib/types';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let collection = $state<Collection | null>(null);

	const backHref = $derived(collection !== null && collection.type === 'source_preset' ? '/' : '/collections');
	const backLabel = $derived(collection !== null && collection.type === 'source_preset' ? '← Gallery' : '← Collections');
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let filters: FilterState = $state({});
	let thumbSize = $state(Number(localStorage.getItem('thumbSize')) || 200);
	let filtersOpen = $state(true);
	let optionsOpen = $state(false);
	let loading = $state(false);
	let currentScrollTop = $state(0);
	let restoredScrollTop = $state(0);
	$effect(() => { localStorage.setItem('thumbSize', String(thumbSize)); });

	beforeNavigate(() => {
		saveScrollPosition(currentScrollTop);
	});

	function collectionId(): number {
		return Number($page.params.id);
	}

	async function fetchImages(reset = false) {
		if (loading) return;
		loading = true;
		try {
			const pg = await listImages({
				cursor: reset ? undefined : (nextCursor ?? undefined),
				limit: 500,
				sort,
				dir,
				collection_id: collectionId(),
				filters,
				show_nsfw: $settingsStore.show_nsfw
			});
			images = reset ? pg.items : [...images, ...pg.items];
			totalCount = pg.total_count;
			nextCursor = pg.next_cursor;
		} finally {
			loading = false;
		}
	}

	async function loadCollectionAndImages() {
		restoredScrollTop = getScrollPosition();
		collection = await fetchCollection(collectionId());
		filters = JSON.parse(localStorage.getItem(`collection:${collectionId()}:filters`) ?? '{}');
		if (collection) {
			sort = collection.sort_by as SortField;
			dir = collection.sort_dir as SortDirection;
			setBrowsingContext({
				type: 'collection',
				collectionId: collection.id,
				name: collection.name,
				filters,
				sort,
				dir
			});
		}
		await fetchImages(true);
	}

	function startSlideshow() {
		if (images.length === 0) return;
		slideshowStore.scheduleStart();
		goto(`/image/${images[0].content_hash}`);
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		fetchImages(true);
		if (collection) {
			setBrowsingContext({
				type: 'collection',
				collectionId: collection.id,
				name: collection.name,
				filters,
				sort,
				dir
			});
			updateCollection(collection.id, { sort_by: newSort, sort_dir: newDir });
		}
	}

	async function toggleNsfw() {
		if (!collection) return;
		const updated = await updateCollection(collection.id, { nsfw: !collection.nsfw });
		collection = updated;
	}

	function onFilterChange(newFilters: FilterState) {
		filters = newFilters;
		localStorage.setItem(`collection:${collectionId()}:filters`, JSON.stringify(newFilters));
		if (collection) {
			setBrowsingContext({
				type: 'collection',
				collectionId: collection.id,
				name: collection.name,
				filters: newFilters,
				sort,
				dir
			});
		}
		fetchImages(true);
	}

	$effect(() => {
		const _id = $page.params.id;
		untrack(() => {
			loadCollectionAndImages();
		});
	});

	// Re-fetch when show_nsfw setting changes (skip before collection is loaded)
	$effect(() => {
		const _ = $settingsStore.show_nsfw;
		untrack(() => { if (collection !== null) fetchImages(true); });
	});

	// Responsive thumb size on mobile
	$effect(() => {
		function updateThumbSize() {
			if (window.innerWidth <= 768) {
				thumbSize = responsiveThumbSize();
			}
		}
		updateThumbSize();
		window.addEventListener('resize', updateThumbSize);
		return () => window.removeEventListener('resize', updateThumbSize);
	});

</script>

<!-- Mobile single-row header -->
<div class="mobile-only">
	<MobilePageHeader
		leftType="back"
		backHref={backHref}
		title={collection?.name ?? ''}
		onMenuOpen={() => (optionsOpen = true)}
	/>
</div>

<!-- Desktop toolbar -->
<div class="toolbar desktop-only">
	<div class="left">
		<a href={backHref}>{backLabel}</a>
		<h2>
			{collection?.name ?? ''}
		</h2>
		{#if collection}
			<button class="nsfw-toggle" class:active={collection.nsfw} onclick={toggleNsfw} title={collection.nsfw ? 'Mark as safe' : 'Mark as NSFW'}>
				NSFW
			</button>
		{/if}
		{#if collection}
			<a class="elo-link" href="/elo/{collection.id}">ELO Vote</a>
		{/if}
		<button class="slideshow-btn" onclick={startSlideshow} disabled={images.length === 0}>Slideshow</button>
	</div>
	<button class="collapse-btn" onclick={() => (filtersOpen = !filtersOpen)} title="Toggle sort controls">⊟</button>
	{#if filtersOpen}
		<div class="filter-row">
			<SortControls {sort} {dir} onchange={onSortChange} />
			<FilterBar {filters} onchange={onFilterChange} />
			<ThumbSizeSlider bind:size={thumbSize} />
		</div>
	{/if}
	<span class="count">{totalCount} images</span>
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
	<div class="sheet-count">{totalCount} images</div>
	<h3 class="sheet-section">Sort by</h3>
	<SortControls {sort} {dir} onchange={(s, d) => { onSortChange(s, d); optionsOpen = false; }} />
	<h3 class="sheet-section">Filter</h3>
	<FilterBar {filters} onchange={(f) => { onFilterChange(f); }} />
	<h3 class="sheet-section">Thumbnail size</h3>
	<ThumbSizeSlider bind:size={thumbSize} />
	{#if collection}
		<h3 class="sheet-section">Collection</h3>
		<label class="sheet-toggle-row">
			<span>NSFW collection</span>
			<input type="checkbox" checked={collection.nsfw} onchange={toggleNsfw} />
		</label>
	{/if}
	<h3 class="sheet-section">Actions</h3>
	<button class="sheet-action-btn" onclick={() => { startSlideshow(); optionsOpen = false; }} disabled={images.length === 0}>Slideshow</button>
	{#if collection}
		<a class="elo-sheet-link" href="/elo/{collection.id}">ELO Vote</a>
	{/if}
</OptionsSheet>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 0 8px;
		flex-shrink: 0;
	}

	.left {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	h2 {
		margin: 0;
		font-size: 1.1rem;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.nsfw-toggle {
		font-size: 0.65rem;
		font-weight: 600;
		padding: 2px 7px;
		border-radius: 3px;
		border: 1px solid #555;
		background: #2a2a2a;
		color: #888;
		cursor: pointer;
		letter-spacing: 0.05em;
		flex-shrink: 0;
	}

	.nsfw-toggle.active {
		background: rgba(122, 42, 42, 0.85);
		border-color: #7a2a2a;
		color: #e08080;
	}

	.sheet-toggle-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 0;
		font-size: 0.9rem;
		color: #ccc;
		cursor: pointer;
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

	.elo-link {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		text-decoration: none;
		font-size: 0.85rem;
		white-space: nowrap;
	}

	.elo-link:hover {
		background: #3a3a3a;
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
		white-space: nowrap;
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

	.count {
		color: #888;
		font-size: 0.85rem;
		padding-right: 8px;
		margin-left: auto;
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

	.elo-sheet-link {
		display: block;
		padding: 12px 0;
		color: #6ea8fe;
		font-size: 0.95rem;
		text-decoration: none;
	}

	.elo-sheet-link:hover {
		color: #90c0ff;
		text-decoration: none;
	}

	@media (max-width: 768px) {
		.mobile-only { display: block; }
		.desktop-only { display: none; }
	}
</style>
