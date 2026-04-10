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
	let error: string | null = $state(null);
	let initialLoad = $state(true);

	async function fetchImages(reset = false) {
		if (loading) return;
		loading = true;
		error = null;
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
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load images';
		} finally {
			loading = false;
			initialLoad = false;
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

{#if error}
	<div class="status error">{error}</div>
{:else if initialLoad}
	<div class="status">Loading…</div>
{:else if totalCount === 0}
	<div class="status empty">
		<p>No images found.</p>
		<p>Add a source folder in <a href="/settings">Settings</a> and trigger a scan.</p>
	</div>
{:else}
	<div class="toolbar">
		<SortControls {sort} {dir} onchange={onSortChange} />
		<span class="count">
			{totalCount} images
			{#if loading}<span class="loading-hint"> (loading…)</span>{/if}
		</span>
	</div>

	<ImageGrid
		{images}
		{totalCount}
		onLoadMore={() => nextCursor && fetchImages()}
	/>
{/if}

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
</style>
