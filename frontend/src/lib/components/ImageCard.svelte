<script lang="ts">
	import type { ImageSummary } from '$lib/types';
	import { thumbUrl } from '$lib/api';

	let { image, size = 200 }: { image: ImageSummary; size?: number } = $props();
</script>

<a href="/image/{image.content_hash}" class="card" class:nsfw={image.nsfw} style="width: {size}px; height: {size}px;">
	<img
		src={thumbUrl(image.content_hash)}
		alt={image.filename}
		loading="lazy"
		decoding="async"
	/>
	{#if image.nsfw}
		<span class="nsfw-badge">NSFW</span>
	{/if}
</a>

<style>
	.card {
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		background: #1a1a1a;
		border-radius: 4px;
		position: relative;
	}

	.card img {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
	}

	.card:hover {
		outline: 2px solid #6ea8fe;
	}

	.nsfw-badge {
		position: absolute;
		top: 4px;
		right: 4px;
		padding: 2px 5px;
		background: rgba(122, 42, 42, 0.9);
		color: #e08080;
		font-size: 0.65rem;
		font-weight: 600;
		border-radius: 3px;
		letter-spacing: 0.05em;
		pointer-events: none;
	}
</style>
