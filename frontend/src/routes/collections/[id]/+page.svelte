<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { listImages, getCollection as fetchCollection } from '$lib/api';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import type { ImageSummary, Collection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';
	import ThumbSizeSlider from '$lib/components/ThumbSizeSlider.svelte';
	import type { SortField, SortDirection } from '$lib/types';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let collection: Collection | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let thumbSize = $state(Number(localStorage.getItem('thumbSize')) || 200);
	let filtersOpen = $state(true);
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
				collection_id: collectionId()
			});
			images = reset ? pg.items : [...images, ...pg.items];
			totalCount = pg.total_count;
			nextCursor = pg.next_cursor;
		} finally {
			loading = false;
		}
	}

	async function loadCollection() {
		collection = await fetchCollection(collectionId());
		if (collection) {
			setBrowsingContext({ type: 'collection', collectionId: collection.id, name: collection.name });
		}
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		fetchImages(true);
	}

	$effect(() => {
		const _id = $page.params.id;
		untrack(() => {
			restoredScrollTop = getScrollPosition();
			loadCollection();
			fetchImages(true);
		});
	});
</script>

<div class="toolbar">
	<div class="left">
		<a href="/collections">← Collections</a>
		<h2>{collection?.name ?? ''}</h2>
		{#if collection}
			<a class="elo-link" href="/elo/{collection.id}">ELO Vote</a>
		{/if}
	</div>
	<button class="collapse-btn" onclick={() => (filtersOpen = !filtersOpen)} title="Toggle sort controls">⊟</button>
	{#if filtersOpen}
		<div class="filter-row">
			<SortControls {sort} {dir} onchange={onSortChange} />
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
	}

	.elo-link:hover {
		background: #3a3a3a;
	}

	.count {
		color: #888;
		font-size: 0.85rem;
		padding-right: 8px;
		margin-left: auto;
	}

	@media (max-width: 768px) {
		.toolbar {
			flex-wrap: wrap;
			padding: 4px 8px;
			gap: 4px;
		}

		.left {
			width: 100%;
			order: 1;
			flex-wrap: wrap;
			gap: 8px;
		}

		h2 {
			font-size: 0.95rem;
		}

		.elo-link {
			padding: 10px 12px;
		}

		.collapse-btn {
			order: 2;
		}

		.count {
			order: 3;
			margin-left: auto;
		}

		.filter-row {
			width: 100%;
			order: 4;
		}
	}
</style>
