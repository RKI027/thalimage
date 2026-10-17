<script lang="ts">
	import type { ImageSummary } from '$lib/types';
	import Icon from '../Icon.svelte';
	import ImagePanel from './ImagePanel.svelte';

	let {
		left,
		right,
		onSelectLeft,
		onSelectRight,
		onArchiveLeft,
		onArchiveRight,
		selectedSide = null
	}: {
		left: ImageSummary;
		right: ImageSummary;
		onSelectLeft?: () => void;
		onSelectRight?: () => void;
		onArchiveLeft?: () => void;
		onArchiveRight?: () => void;
		selectedSide?: 'left' | 'right' | null;
	} = $props();
</script>

{#snippet panel(item: ImageSummary, selected: boolean, onSelect?: () => void, onArchive?: () => void)}
	<div class="slot">
		<ImagePanel hash={item.content_hash} filename={item.filename} {selected} onclick={onSelect} />
		{#if onArchive}
			<button class="archive" type="button" title="Archive this image and skip the pair" aria-label="Archive" onclick={onArchive}>
				<Icon name="archive" size={18} />
			</button>
		{/if}
	</div>
{/snippet}

<div class="side-by-side">
	{@render panel(left, selectedSide === 'left', onSelectLeft, onArchiveLeft)}
	<div class="divider"></div>
	{@render panel(right, selectedSide === 'right', onSelectRight, onArchiveRight)}
</div>

<style>
	.side-by-side {
		flex: 1;
		display: flex;
		min-height: 0;
		gap: 0;
	}

	.slot {
		position: relative;
		flex: 1;
		display: flex;
		min-width: 0;
		min-height: 0;
	}

	.archive {
		position: absolute;
		top: 12px;
		right: 12px;
		display: flex;
		padding: 8px;
		border: 1px solid #444;
		border-radius: 6px;
		background: rgba(0, 0, 0, 0.6);
		color: #ccc;
		cursor: pointer;
	}

	.archive:hover {
		color: #fff;
		border-color: #888;
	}

	.divider {
		width: 2px;
		background: #333;
		flex-shrink: 0;
	}

	@media (max-width: 768px) {
		.side-by-side {
			flex-direction: column;
		}

		.divider {
			width: 100%;
			height: 2px;
		}
	}
</style>
