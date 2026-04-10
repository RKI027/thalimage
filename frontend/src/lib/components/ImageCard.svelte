<script lang="ts">
	import type { ImageSummary } from '$lib/types';
	import { thumbUrl } from '$lib/api';

	let { image, size = 200 }: { image: ImageSummary; size?: number } = $props();
</script>

<a href="/image/{image.content_hash}" class="card" style="width: {size}px; height: {size}px;">
	<img
		src={thumbUrl(image.content_hash)}
		alt={image.filename}
		loading="lazy"
		decoding="async"
	/>
</a>

<style>
	.card {
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		background: #1a1a1a;
		border-radius: 4px;
	}

	.card img {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
	}

	.card:hover {
		outline: 2px solid #6ea8fe;
	}
</style>
