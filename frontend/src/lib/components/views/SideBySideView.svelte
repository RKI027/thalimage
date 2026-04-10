<script lang="ts">
	import type { ImageSummary } from '$lib/types';
	import ImagePanel from './ImagePanel.svelte';

	let {
		left,
		right,
		onSelectLeft,
		onSelectRight,
		selectedSide = null
	}: {
		left: ImageSummary;
		right: ImageSummary;
		onSelectLeft?: () => void;
		onSelectRight?: () => void;
		selectedSide?: 'left' | 'right' | null;
	} = $props();
</script>

<div class="side-by-side">
	<ImagePanel
		hash={left.content_hash}
		filename={left.filename}
		selected={selectedSide === 'left'}
		onclick={onSelectLeft}
	/>
	<div class="divider"></div>
	<ImagePanel
		hash={right.content_hash}
		filename={right.filename}
		selected={selectedSide === 'right'}
		onclick={onSelectRight}
	/>
</div>

<style>
	.side-by-side {
		flex: 1;
		display: flex;
		min-height: 0;
		gap: 0;
	}

	.divider {
		width: 2px;
		background: #333;
		flex-shrink: 0;
	}
</style>
