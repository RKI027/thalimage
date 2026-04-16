<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { listImages } from '$lib/api';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import type { ImageSummary, SortField, SortDirection } from '$lib/types';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';
	import ThumbSizeSlider from '$lib/components/ThumbSizeSlider.svelte';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
	let sourceId: number | undefined = $state(undefined);
	let thumbSize = $state(Number(localStorage.getItem('thumbSize')) || 200);
	let filtersOpen = $state(true);
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
		setBrowsingContext({ type: 'all' });
		restoredScrollTop = getScrollPosition();
		sourceId = readSourceId();
		fetchImages(true);
	});

	// Re-fetch when source_id query param changes (clicking different sources)
	$effect(() => {
		const newId = readSourceId();
		untrack(() => {
			if (newId !== sourceId) {
				sourceId = newId;
				fetchImages(true);
			}
		});
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
	<div class="toolbar">
		<button class="collapse-btn" onclick={() => (filtersOpen = !filtersOpen)} title="Toggle sort controls">⊟</button>
		{#if filtersOpen}
			<div class="filter-row">
				<SortControls {sort} {dir} onchange={onSortChange} />
				<ThumbSizeSlider bind:size={thumbSize} />
			</div>
		{/if}
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

	@media (max-width: 768px) {
		.toolbar {
			flex-wrap: wrap;
			padding: 4px 8px;
			gap: 4px;
		}

		.collapse-btn {
			order: 1;
		}

		.count {
			order: 2;
			margin-left: auto;
		}

		.filter-row {
			width: 100%;
			order: 3;
		}
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
