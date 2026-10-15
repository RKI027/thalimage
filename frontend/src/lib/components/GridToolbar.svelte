<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { FilterState, SortField, SortDirection } from '$lib/types';
	import SortControls from './SortControls.svelte';
	import FilterBar from './FilterBar.svelte';
	import ThumbSizeSlider from './ThumbSizeSlider.svelte';
	import MobilePageHeader from './MobilePageHeader.svelte';
	import OptionsSheet from './OptionsSheet.svelte';
	import { activeFilterCount } from '$lib/filters';

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

	let filtersOpen = $state(false);
	let optionsOpen = $state(false);
	let filtersEl: HTMLElement | undefined = $state();
	const filterCount = $derived(activeFilterCount(filters));

	function closeFiltersOutside(e: PointerEvent) {
		if (filtersOpen && filtersEl && !filtersEl.contains(e.target as Node)) filtersOpen = false;
	}
</script>

<svelte:window
	onpointerdown={closeFiltersOutside}
	onkeydown={(e) => { if (e.key === 'Escape') filtersOpen = false; }}
/>

<!-- Mobile single-row header -->
<div class="mobile-only">
	<MobilePageHeader {leftType} {backHref} {title} onMenuOpen={() => (optionsOpen = true)} />
</div>

<!-- Desktop toolbar -->
<div class="toolbar desktop-only">
	{#if desktopLeading}{@render desktopLeading()}{/if}
	<div class="group">
		<SortControls {sort} {dir} {allowElo} onchange={onSortChange} />
		<div class="filters" bind:this={filtersEl}>
			<button
				class="control"
				class:active={filterCount > 0}
				aria-expanded={filtersOpen}
				onclick={() => (filtersOpen = !filtersOpen)}
			>
				Filters{#if filterCount > 0}<span class="badge">{filterCount}</span>{/if}
			</button>
			{#if filtersOpen}
				<div class="filters-panel">
					<FilterBar {filters} {allowElo} onchange={onFilterChange} />
				</div>
			{/if}
		</div>
	</div>
	<div class="group actions">
		{#if desktopActions}{@render desktopActions()}{/if}
		<button class="control" onclick={onStartSlideshow} {disabled}>Slideshow</button>
	</div>
	<!-- The count and slider keep their place at the right edge: the count's
	     width is reserved, and loading dims it rather than adding text. -->
	<div class="group view">
		<span class="count" class:loading title={loading ? 'Loading…' : undefined}>{count} images</span>
		<ThumbSizeSlider bind:size={thumbSize} />
	</div>
</div>

<!-- Mobile options sheet -->
<OptionsSheet open={optionsOpen} onclose={() => (optionsOpen = false)}>
	<div class="sheet-count">{count} images{#if loading} (loading…){/if}</div>
	<h3 class="sheet-section">Sort by</h3>
	<SortControls {sort} {dir} {allowElo} onchange={(s, d) => { onSortChange(s, d); optionsOpen = false; }} />
	<h3 class="sheet-section">Filter</h3>
	<FilterBar {filters} {allowElo} onchange={(f) => onFilterChange(f)} />
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
		flex-wrap: wrap;
		gap: 4px 24px;
		padding: 4px 8px;
		flex-shrink: 0;
	}

	.group {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	/* On a narrow window the count and slider wrap together, still at the right. */
	.actions,
	.view {
		margin-left: auto;
	}

	.filters {
		position: relative;
	}

	.filters .active {
		border-color: var(--control-focus);
	}

	.badge {
		margin-left: 6px;
		padding: 0 6px;
		border-radius: 8px;
		background: var(--control-primary-bg);
		color: var(--control-primary-text);
		font-size: 0.75rem;
	}

	.filters-panel {
		position: absolute;
		top: calc(100% + 4px);
		left: 0;
		z-index: 30;
		min-width: 280px;
		padding: 8px;
		background: #1a1a1a;
		border: 1px solid #444;
		border-radius: 6px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
	}

	/* A sheet action spans the sheet rather than hugging its label. */
	.sheet-action-btn {
		display: flex;
		width: 100%;
		justify-content: center;
		margin-top: 6px;
	}

	.count {
		min-width: 8em;
		text-align: right;
		color: #888;
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.count.loading {
		opacity: 0.5;
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
