<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { FilterState, SortField, SortDirection } from '$lib/types';
	import SortControls from './SortControls.svelte';
	import FilterBar from './FilterBar.svelte';
	import ThumbSizeSlider from './ThumbSizeSlider.svelte';
	import MobilePageHeader from './MobilePageHeader.svelte';
	import OptionsSheet from './OptionsSheet.svelte';

	let {
		sort,
		dir,
		filters,
		thumbSize = $bindable(),
		count,
		loading = false,
		disabled = false,
		allowElo = false,
		title,
		leftType,
		backHref,
		onSortChange,
		onFilterChange,
		onStartSlideshow,
		desktopLeading,
		desktopActions,
		sheetExtras,
		sheetActions
	}: {
		sort: SortField;
		dir: SortDirection;
		filters: FilterState;
		thumbSize: number;
		count: number;
		loading?: boolean;
		disabled?: boolean;
		allowElo?: boolean;
		title: string;
		leftType: 'hamburger' | 'back';
		backHref?: string;
		onSortChange: (sort: SortField, dir: SortDirection) => void;
		onFilterChange: (filters: FilterState) => void;
		onStartSlideshow: () => void;
		/** Desktop: page-specific chrome at the far left (e.g. back link + title). */
		desktopLeading?: Snippet;
		/** Desktop: page-specific actions just before the Slideshow button. */
		desktopActions?: Snippet;
		/** Mobile sheet: page-specific section before the Actions heading. */
		sheetExtras?: Snippet;
		/** Mobile sheet: page-specific actions after the Slideshow button. */
		sheetActions?: Snippet;
	} = $props();

	let filtersOpen = $state(true);
	let optionsOpen = $state(false);
</script>

<!-- Mobile single-row header -->
<div class="mobile-only">
	<MobilePageHeader {leftType} {backHref} {title} onMenuOpen={() => (optionsOpen = true)} />
</div>

<!-- Desktop toolbar -->
<div class="toolbar desktop-only">
	{#if desktopLeading}{@render desktopLeading()}{/if}
	<button class="collapse-btn" onclick={() => (filtersOpen = !filtersOpen)} title="Toggle sort controls">⊟</button>
	{#if filtersOpen}
		<div class="filter-row">
			<SortControls {sort} {dir} {allowElo} onchange={onSortChange} />
			<FilterBar {filters} onchange={onFilterChange} />
			<ThumbSizeSlider bind:size={thumbSize} />
		</div>
	{/if}
	{#if desktopActions}{@render desktopActions()}{/if}
	<button class="control slideshow-btn" onclick={onStartSlideshow} {disabled}>Slideshow</button>
	<span class="count">
		{count} images{#if loading}<span class="loading-hint"> (loading…)</span>{/if}
	</span>
</div>

<!-- Mobile options sheet -->
<OptionsSheet open={optionsOpen} onclose={() => (optionsOpen = false)}>
	<div class="sheet-count">{count} images{#if loading} (loading…){/if}</div>
	<h3 class="sheet-section">Sort by</h3>
	<SortControls {sort} {dir} {allowElo} onchange={(s, d) => { onSortChange(s, d); optionsOpen = false; }} />
	<h3 class="sheet-section">Filter</h3>
	<FilterBar {filters} onchange={(f) => onFilterChange(f)} />
	<h3 class="sheet-section">Thumbnail size</h3>
	<ThumbSizeSlider bind:size={thumbSize} />
	{#if sheetExtras}{@render sheetExtras()}{/if}
	<h3 class="sheet-section">Actions</h3>
	<button class="control sheet-action-btn" onclick={() => { onStartSlideshow(); optionsOpen = false; }} {disabled}>Slideshow</button>
	{#if sheetActions}{@render sheetActions()}{/if}
</OptionsSheet>

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

	.slideshow-btn {
		flex-shrink: 0;
	}

	/* A sheet action spans the sheet rather than hugging its label. */
	.sheet-action-btn {
		display: flex;
		width: 100%;
		justify-content: center;
		margin-top: 6px;
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

	.loading-hint {
		color: #666;
	}

	.sheet-count {
		color: #888;
		font-size: 0.85rem;
		margin-bottom: 16px;
	}

	/* Snippet content injected by pages is scoped to the page, so pages that add
	   their own sheet section (e.g. the collection's NSFW toggle) must re-declare
	   a matching `.sheet-section` there. Keep the two in sync. */
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

	/* Mobile/desktop visibility */
	.mobile-only { display: none; }
	.desktop-only { display: flex; }

	@media (max-width: 768px) {
		.mobile-only { display: block; }
		.desktop-only { display: none; }
	}
</style>
