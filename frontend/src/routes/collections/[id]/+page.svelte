<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { listImages, getCollection as fetchCollection } from '$lib/api';
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
	let loading = $state(false);

	$effect(() => { localStorage.setItem('thumbSize', String(thumbSize)); });

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
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		fetchImages(true);
	}

	$effect(() => {
		const _id = $page.params.id;
		untrack(() => {
			loadCollection();
			fetchImages(true);
		});
	});
</script>

<div class="toolbar">
	<div class="left">
		<a href="/collections">← Collections</a>
		<h2>{collection?.name ?? ''}</h2>
	</div>
	<SortControls {sort} {dir} onchange={onSortChange} />
	<ThumbSizeSlider bind:size={thumbSize} />
	{#if collection}
		<a class="elo-link" href="/elo/{collection.id}">ELO Vote</a>
	{/if}
	<span class="count">{totalCount} images</span>
</div>

<ImageGrid {images} {totalCount} thumbSize={thumbSize} onLoadMore={() => nextCursor && fetchImages()} />

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
</style>
