<script lang="ts">
	import { imageFileUrl } from '$lib/api';

	let {
		hash,
		filename,
		selected = false,
		onclick
	}: {
		hash: string;
		filename: string;
		selected?: boolean;
		onclick?: () => void;
	} = $props();
</script>

<button class="image-panel" class:selected onclick={onclick} type="button">
	<img
		src={imageFileUrl(hash)}
		alt={filename}
	/>
</button>

<style>
	.image-panel {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		background: #000;
		min-height: 0;
		border: 3px solid transparent;
		padding: 0;
		cursor: pointer;
		transition: border-color 0.15s;
	}

	.image-panel:hover {
		border-color: #444;
	}

	.image-panel.selected {
		border-color: #6ea8fe;
	}

	img {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
	}
</style>
