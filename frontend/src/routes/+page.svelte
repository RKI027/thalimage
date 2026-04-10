<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { listImages } from '$lib/api';
	import type { ImageSummary, SortField, SortDirection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let sourceId: number | undefined = $state(undefined);
	let loading = $state(false);
	let error: string | null = $state(null);
	let initialLoad = $state(true);

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
				source_id: sourceId
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

	function onSortChange(newSort: SortField, newDir: SortDirection) {
		sort = newSort;
		dir = newDir;
		fetchImages(true);
	}

	function readSourceId(): number | undefined {
		const v = $page.url.searchParams.get('source_id');
		return v ? Number(v) : undefined;
	}

	onMount(() => {
		sourceId = readSourceId();
		fetchImages(true);
	});

	// Re-fetch when source_id query param changes (clicking different sources)
	$effect(() => {
		const newId = readSourceId();
		if (newId !== sourceId) {
			sourceId = newId;
			fetchImages(true);
		}
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
