<script lang="ts">
	import { imageFileUrl, thumbUrl } from '$lib/api';

	const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);

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

	const isVideo = $derived(
		VIDEO_EXTENSIONS.has(filename.slice(filename.lastIndexOf('.')).toLowerCase())
	);

	let loaded = $state(false);
	let videoEl = $state<HTMLVideoElement | null>(null);
	$effect(() => {
		void hash;
		loaded = false;
	});

	// Autoplay the preview muted so video pairs can be judged in motion. The
	// element carries no controls, so a tap falls through to the panel and casts
	// a vote rather than toggling playback.
	$effect(() => {
		const v = videoEl;
		if (!v) return;
		v.muted = true;
		v.play().catch(() => {});
	});
</script>

<button class="image-panel" class:selected onclick={onclick} type="button">
	{#if isVideo}
		<!-- svelte-ignore a11y_media_has_caption -->
		<video
			bind:this={videoEl}
			src={imageFileUrl(hash)}
			poster={thumbUrl(hash)}
			autoplay
			muted
			loop
			playsinline
			preload="auto"
			onloadeddata={() => (loaded = true)}
			onerror={() => (loaded = true)}
		></video>
	{:else}
		<img
			src={imageFileUrl(hash)}
			alt={filename}
			onload={() => (loaded = true)}
			onerror={() => (loaded = true)}
		/>
	{/if}
	{#if !loaded}
		<div class="loading-spinner" aria-label="Loading"></div>
	{/if}
</button>

<style>
	.image-panel {
		position: relative;
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

	.loading-spinner {
		position: absolute;
		top: 50%;
		left: 50%;
		width: 32px;
		height: 32px;
		margin: -16px 0 0 -16px;
		border: 3px solid rgba(255, 255, 255, 0.25);
		border-top-color: rgba(255, 255, 255, 0.85);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		pointer-events: none;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.image-panel:hover {
		border-color: #444;
	}

	.image-panel.selected {
		border-color: #6ea8fe;
	}

	img,
	video {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
	}
</style>
