<script lang="ts">
	import { untrack } from 'svelte';
	import type { ImageSummary } from '$lib/types';
	import type { ImageSelection } from '$lib/imageSelection.svelte';
	import { needsMoreImages } from '$lib/gridPaging';
	import ImageCard from './ImageCard.svelte';

	let {
		images,
		totalCount,
		thumbSize = 200,
		gap = 8,
		initialScrollTop = 0,
		selection,
		onLoadMore,
		onScroll: onScrollCallback
	}: {
		images: ImageSummary[];
		totalCount: number;
		thumbSize?: number;
		gap?: number;
		initialScrollTop?: number;
		selection?: ImageSelection;
		onLoadMore?: () => void;
		onScroll?: (scrollTop: number) => void;
	} = $props();

	let containerEl: HTMLDivElement | undefined = $state();
	let containerWidth = $state(0);
	let scrollTop = $state(0);
	let viewportHeight = $state(0);

	const cellSize = $derived(thumbSize + gap);
	const columns = $derived(Math.max(1, Math.floor((containerWidth + gap) / cellSize)));
	const totalRows = $derived(Math.ceil(totalCount / columns));
	const totalHeight = $derived(totalRows * cellSize);

	const startRow = $derived(Math.max(0, Math.floor(scrollTop / cellSize) - 2));
	const endRow = $derived(Math.min(totalRows, Math.ceil((scrollTop + viewportHeight) / cellSize) + 2));
	const visibleStart = $derived(startRow * columns);
	const visibleEnd = $derived(Math.min(images.length, endRow * columns));

	// While selecting, a click selects rather than opens; Ctrl/Cmd-click
	// starts selecting. Shift-click on a link otherwise opens a window.
	function onCardClick(e: MouseEvent, hash: string) {
		if (!selection || !(selection.active || e.ctrlKey || e.metaKey)) return;
		e.preventDefault();
		selection.click(hash, { range: e.shiftKey });
	}

	function onScroll() {
		if (!containerEl) return;
		scrollTop = containerEl.scrollTop;
		onScrollCallback?.(scrollTop);
	}

	// Checked whenever a page lands or the view moves, not only on scroll: a
	// page can arrive while the viewport is still past the loaded images.
	$effect(() => {
		const position = {
			loaded: images.length,
			total: totalCount,
			columns,
			cellSize,
			scrollTop,
			viewportHeight
		};
		if (onLoadMore && needsMoreImages(position)) untrack(() => onLoadMore());
	});

	function onResize(entries: ResizeObserverEntry[]) {
		const entry = entries[0];
		if (entry) {
			containerWidth = entry.contentRect.width;
			viewportHeight = entry.contentRect.height;
		}
	}

	let scrollRestored = false;

	$effect(() => {
		if (!containerEl) return;
		const observer = new ResizeObserver(onResize);
		observer.observe(containerEl);
		return () => observer.disconnect();
	});

	$effect(() => {
		if (!scrollRestored && containerEl && images.length > 0 && containerWidth > 0 && initialScrollTop > 0) {
			containerEl.scrollTop = initialScrollTop;
			scrollRestored = true;
		}
	});
</script>

<div class="grid-container" bind:this={containerEl} onscroll={onScroll}>
	<div class="grid-spacer" style="height: {totalHeight}px;">
		{#each images.slice(visibleStart, visibleEnd) as image, i (image.content_hash)}
			{@const index = visibleStart + i}
			{@const row = Math.floor(index / columns)}
			{@const col = index % columns}
			<div
				class="grid-cell"
				style="
					position: absolute;
					top: {row * cellSize}px;
					left: {col * cellSize}px;
					width: {thumbSize}px;
					height: {thumbSize}px;
				"
			>
				<ImageCard
					{image}
					size={thumbSize}
					selected={selection?.has(image.content_hash) ?? false}
					onclick={(e) => onCardClick(e, image.content_hash)}
				/>
			</div>
		{/each}
	</div>
</div>

<style>
	.grid-container {
		overflow-y: auto;
		overscroll-behavior-y: contain;
		height: 100%;
		position: relative;
	}

	.grid-spacer {
		position: relative;
		width: 100%;
	}
</style>
