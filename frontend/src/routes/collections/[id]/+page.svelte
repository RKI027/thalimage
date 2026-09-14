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
	import GridToolbar from '$lib/components/GridToolbar.svelte';
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

<GridToolbar
	{sort}
	{dir}
	{filters}
	bind:thumbSize
	count={totalCount}
	{loading}
	disabled={images.length === 0}
	allowElo
	title={collection?.name ?? ''}
	leftType="back"
	{backHref}
	{onSortChange}
	{onFilterChange}
	onStartSlideshow={startSlideshow}
>
	{#snippet desktopLeading()}
		<div class="left">
			<a href={backHref}>{backLabel}</a>
			<h2>{collection?.name ?? ''}</h2>
			{#if collection}
				<button class="nsfw-toggle" class:active={collection.nsfw} onclick={toggleNsfw} title={collection.nsfw ? 'Mark as safe' : 'Mark as NSFW'}>
					NSFW
				</button>
			{/if}
		</div>
	{/snippet}
	{#snippet desktopActions()}
		{#if collection}
			<a class="control" href="/elo/{collection.id}">ELO Vote</a>
		{/if}
	{/snippet}
	{#snippet sheetExtras()}
		{#if collection}
			<h3 class="sheet-section">Collection</h3>
			<label class="sheet-toggle-row">
				<span>NSFW collection</span>
				<input type="checkbox" checked={collection.nsfw} onchange={toggleNsfw} />
			</label>
		{/if}
	{/snippet}
	{#snippet sheetActions()}
		{#if collection}
			<a class="control elo-sheet-link" href="/elo/{collection.id}">ELO Vote</a>
		{/if}
	{/snippet}
</GridToolbar>

<ImageGrid
	{images}
	{totalCount}
	thumbSize={thumbSize}
	initialScrollTop={restoredScrollTop}
	onLoadMore={() => nextCursor && fetchImages()}
	onScroll={(s) => { currentScrollTop = s; }}
/>

<style>
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

	/* Injected into GridToolbar's options sheet; mirrors its section heading. */
	.sheet-section {
		margin: 16px 0 8px;
		font-size: 0.8rem;
		color: #6ea8fe;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.elo-sheet-link {
		display: flex;
		width: 100%;
		justify-content: center;
		margin-top: 6px;
	}

	.elo-sheet-link:hover {
		color: #90c0ff;
		text-decoration: none;
	}
</style>
