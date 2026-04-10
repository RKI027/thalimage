<script lang="ts">
	import { page } from '$app/stores';
	import { listImages } from '$lib/api';
	import { listCollections } from '$lib/api';
	import type { ImageSummary, Collection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';
	import type { SortField, SortDirection } from '$lib/types';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let collection: Collection | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let loading = $state(false);

	async function fetchImages(reset = false) {
		if (loading) return;
		const id = Number($page.params.id);
		loading = true;
		try {
			const pg = await listImages({
				cursor: reset ? undefined : (nextCursor ?? undefined),
				limit: 500,
				sort,
				dir,
				collection_id: id
			});
			images = reset ? pg.items : [...images, ...pg.items];
			totalCount = pg.total_count;
			nextCursor = pg.next_cursor;
		} finally {
			loading = false;
		}
	}

	async function loadCollection() {
		const id = Number($page.params.id);
		const colls = await listCollections();
		collection = colls.find((c) => c.id === id) ?? null;
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		fetchImages(true);
	}

	$effect(() => {
		const _id = $page.params.id;
		loadCollection();
		fetchImages(true);
	});
</script>

{#if collection}
	<div class="toolbar">
		<div class="left">
			<a href="/collections">← Collections</a>
			<h2>{collection.name}</h2>
		</div>
		<SortControls {sort} {dir} onchange={onSortChange} />
		<span class="count">{totalCount} images</span>
	</div>

	<ImageGrid {images} {totalCount} onLoadMore={() => nextCursor && fetchImages()} />
{:else}
	<div class="loading">Loading…</div>
{/if}

<style>
	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
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

	.count {
		color: #888;
		font-size: 0.85rem;
		padding-right: 8px;
	}

	.loading {
		padding: 32px;
		color: #888;
		text-align: center;
	}
</style>
