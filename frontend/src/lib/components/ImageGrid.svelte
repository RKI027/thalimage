<script lang="ts">
	import type { ImageSummary } from '$lib/types';
	import ImageCard from './ImageCard.svelte';

	let {
		images,
		totalCount,
		thumbSize = 200,
		gap = 8,
		initialScrollTop = 0,
		onLoadMore,
		onScroll: onScrollCallback
	}: {
		images: ImageSummary[];
		totalCount: number;
		thumbSize?: number;
		gap?: number;
		initialScrollTop?: number;
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

	function onScroll() {
		if (!containerEl) return;
		scrollTop = containerEl.scrollTop;
		onScrollCallback?.(scrollTop);

		// Pre-fetch at 70% scroll through loaded items
		const scrollRatio = (scrollTop + viewportHeight) / totalHeight;
		if (scrollRatio > 0.7 && images.length < totalCount && onLoadMore) {
			onLoadMore();
		}
	}

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
				<ImageCard {image} size={thumbSize} />
			</div>
		{/each}
	</div>
</div>

<style>
	.grid-container {
		overflow-y: auto;
		height: 100%;
		position: relative;
	}

	.grid-spacer {
		position: relative;
		width: 100%;
	}
</style>
