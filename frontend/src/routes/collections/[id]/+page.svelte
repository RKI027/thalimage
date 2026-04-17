<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { beforeNavigate } from '$app/navigation';
	import { listImages, getCollection as fetchCollection } from '$lib/api';
	import { setBrowsingContext, saveScrollPosition, getScrollPosition } from '$lib/browsingContext';
	import type { ImageSummary, Collection } from '$lib/types';
	import { responsiveThumbSize } from '$lib/mobileStore.svelte';
	import ImageGrid from '$lib/components/ImageGrid.svelte';
	import SortControls from '$lib/components/SortControls.svelte';
	import ThumbSizeSlider from '$lib/components/ThumbSizeSlider.svelte';
	import MobilePageHeader from '$lib/components/MobilePageHeader.svelte';
	import type { SortField, SortDirection } from '$lib/types';

	let images: ImageSummary[] = $state([]);
	let totalCount = $state(0);
	let nextCursor: string | null = $state(null);
	let collection: Collection | null = $state(null);
	let sort: SortField = $state('name');
	let dir: SortDirection = $state('asc');
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
		backHref="/collections"
		title={collection?.name ?? ''}
		onMenuOpen={() => (optionsOpen = true)}
	/>
</div>

<!-- Desktop toolbar -->
<div class="toolbar desktop-only">
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

<!-- Mobile options sheet -->
{#if optionsOpen}
	<button class="sheet-backdrop" onclick={() => (optionsOpen = false)} aria-label="Close menu"></button>
	<div class="options-sheet">
		<div class="sheet-handle"></div>
		<div class="sheet-content">
			<div class="sheet-count">{totalCount} images</div>
			<h3 class="sheet-section">Sort by</h3>
			<SortControls {sort} {dir} onchange={(s, d) => { onSortChange(s, d); optionsOpen = false; }} />
			<h3 class="sheet-section">Thumbnail size</h3>
			<ThumbSizeSlider bind:size={thumbSize} />
			{#if collection}
				<h3 class="sheet-section">Actions</h3>
				<a class="elo-sheet-link" href="/elo/{collection.id}">ELO Vote →</a>
			{/if}
		</div>
	</div>
{/if}

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

	/* Mobile/desktop visibility */
	.mobile-only { display: none; }
	.desktop-only { display: flex; }

	/* Options sheet */
	.sheet-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 50;
		border: none;
		cursor: default;
	}

	.options-sheet {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		background: #1a1a1a;
		border-top: 1px solid #444;
		border-radius: 16px 16px 0 0;
		z-index: 60;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		animation: sheet-up 0.25s ease;
	}

	@keyframes sheet-up {
		from { transform: translateY(100%); }
		to   { transform: translateY(0); }
	}

	.sheet-handle {
		width: 40px;
		height: 4px;
		background: #555;
		border-radius: 2px;
		margin: 10px auto 4px;
		flex-shrink: 0;
	}

	.sheet-content {
		padding: 8px 16px 24px;
		overflow-y: auto;
	}

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

		.options-sheet :global(.thumb-slider) {
			width: 100%;
		}

		.options-sheet :global(input[type='range']) {
			width: 100%;
		}
	}
</style>
