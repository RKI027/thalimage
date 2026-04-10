<script lang="ts">
	import { imageFileUrl } from '$lib/api';

	let {
		hash,
		filename,
		width,
		height
	}: {
		hash: string;
		filename: string;
		width: number;
		height: number;
	} = $props();
</script>

<div class="viewer">
	<img
		src={imageFileUrl(hash)}
		alt={filename}
		style="max-width: 100%; max-height: 100%; object-fit: contain;"
	/>
</div>

<style>
	.viewer {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		background: #000;
		min-height: 0;
	}
</style>
