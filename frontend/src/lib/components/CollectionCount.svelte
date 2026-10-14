<script lang="ts">
	import Icon from './Icon.svelte';
	import Tooltip from './Tooltip.svelte';

	/**
	 * A collection's image count as browsing shows it, with its archived
	 * images counted apart when it has any. `unit` adds the word "images".
	 */
	let {
		imageCount,
		archivedCount,
		unit = false
	}: { imageCount: number; archivedCount: number; unit?: boolean } = $props();

	const archivedText = $derived(
		`${archivedCount} archived ${archivedCount === 1 ? 'image' : 'images'}, not shown when browsing`
	);
</script>

<span class="collection-count">
	{imageCount}{unit ? ' images' : ''}
	{#if archivedCount > 0}
		<Tooltip text={archivedText}>
			<span class="archived">
				<Icon name="archive" size={12} />{archivedCount}
				<span class="screen-reader">{archivedText}</span>
			</span>
		</Tooltip>
	{/if}
</span>

<style>
	.collection-count {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	.archived {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		opacity: 0.8;
	}

	.screen-reader {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
