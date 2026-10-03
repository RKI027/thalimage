<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { getCollection as fetchCollection, updateCollection } from '$lib/api';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import { Gallery, collectionFiltersKey } from '$lib/gallery.svelte';
	import { readStored, writeStored } from '$lib/storage';
	import { settingsStore } from '$lib/stores';
	import type { Collection, FilterState, SortField, SortDirection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import GridToolbar from '$lib/components/GridToolbar.svelte';

	let collection = $state<Collection | null>(null);

	const backHref = $derived(collection !== null && collection.type === 'source_preset' ? '/' : '/collections');
	const backLabel = $derived(collection !== null && collection.type === 'source_preset' ? '← Gallery' : '← Collections');
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let filters: FilterState = $state({});
	let currentScrollTop = $state(0);
	let restoredScrollTop = $state(0);

	const gallery = new Gallery(() => ({
		sort,
		dir,
		collection_id: collectionId(),
		filters,
		show_nsfw: $settingsStore.show_nsfw
	}));

	beforeNavigate(() => {
		saveScrollPosition(currentScrollTop);
	});

	function collectionId(): number {
		return Number($page.params.id);
	}

	// The viewer walks prev/next through exactly this listing.
	function rememberContext() {
		if (!collection) return;
		setBrowsingContext({
			type: 'collection',
			collectionId: collection.id,
			name: collection.name,
			filters,
			sort,
			dir
		});
	}

	async function loadCollectionAndImages() {
		const id = collectionId();
		restoredScrollTop = getScrollPosition();
		const loaded = await fetchCollection(id);
		if (id !== collectionId()) return; // navigated on meanwhile
		collection = loaded;
		filters = readStored<FilterState>(collectionFiltersKey(id), {});
		sort = loaded.sort_by as SortField;
		dir = loaded.sort_dir as SortDirection;
		rememberContext();
		// Supersedes anything the previous collection still has in flight.
		await gallery.reset();
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		gallery.reset();
		rememberContext();
		if (collection) updateCollection(collection.id, { sort_by: newSort, sort_dir: newDir });
	}

	async function toggleNsfw() {
		if (!collection) return;
		const updated = await updateCollection(collection.id, { nsfw: !collection.nsfw });
		collection = updated;
	}

	function onFilterChange(newFilters: FilterState) {
		filters = newFilters;
		writeStored(collectionFiltersKey(collectionId()), newFilters);
		rememberContext();
		gallery.reset();
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
		untrack(() => { if (collection !== null) gallery.reset(); });
	});

	$effect(() => gallery.followViewport());

</script>

<GridToolbar
	{sort}
	{dir}
	{filters}
	bind:thumbSize={gallery.thumbSize}
	count={gallery.totalCount}
	loading={gallery.loading}
	disabled={gallery.images.length === 0}
	allowElo
	title={collection?.name ?? ''}
	leftType="back"
	{backHref}
	{onSortChange}
	{onFilterChange}
	onStartSlideshow={() => gallery.startSlideshow()}
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

{#if gallery.error}
	<div class="status error">{gallery.error}</div>
{/if}

<ImageGrid
	images={gallery.images}
	totalCount={gallery.totalCount}
	thumbSize={gallery.thumbSize}
	initialScrollTop={restoredScrollTop}
	onLoadMore={() => gallery.loadMore()}
	onScroll={(s) => { currentScrollTop = s; }}
/>

<style>
	.status.error {
		padding: 24px;
		text-align: center;
		color: #f66;
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
