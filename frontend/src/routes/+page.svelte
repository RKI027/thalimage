<script lang="ts">
	import { listImages } from '$lib/api';
	import type { ImageSummary, SortField, SortDirection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let loading = $state(false);

	async function fetchImages(reset = false) {
		if (loading) return;
		loading = true;
		try {
			const page = await listImages({
				cursor: reset ? undefined : (nextCursor ?? undefined),
				limit: 500,
				sort,
				dir
			});
			if (reset) {
				images = page.items;
			} else {
				images = [...images, ...page.items];
			}
			totalCount = page.total_count;
			nextCursor = page.next_cursor;
		} finally {
			loading = false;
		}
	}

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		fetchImages(true);
	}

	$effect(() => {
		fetchImages(true);
	});
</script>

<div class="toolbar">
	<SortControls {sort} {dir} onchange={onSortChange} />
	<span class="count">{totalCount} images</span>
</div>

<ImageGrid
	{images}
	{totalCount}
	onLoadMore={() => nextCursor && fetchImages()}
/>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 8px;
		flex-shrink: 0;
	}

	.count {
		color: #888;
		font-size: 0.85rem;
		padding-right: 8px;
	}
</style>
