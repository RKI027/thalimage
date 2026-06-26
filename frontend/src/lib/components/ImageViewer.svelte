<script lang="ts">
	import { imageFileUrl, thumbUrl } from '$lib/api';

	const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);

	let {
		hash,
		filename,
		width,
		height,
		loop = false,
		videoEl = $bindable(null)
	}: {
		hash: string;
		filename: string;
		width: number;
		height: number;
		loop?: boolean;
		videoEl?: HTMLVideoElement | null;
	} = $props();

	const isVideo = $derived(
		VIDEO_EXTENSIONS.has(filename.slice(filename.lastIndexOf('.')).toLowerCase())
	);

	let loaded = $state(false);
	// Reset the loading state whenever the source changes.
	$effect(() => {
		void hash;
		loaded = false;
	});

	$effect(() => {
		if (!videoEl) return;
		videoEl.volume = parseFloat(localStorage.getItem('video:volume') ?? '1');
		videoEl.muted = localStorage.getItem('video:muted') === 'true';

		function onVolumeChange() {
			localStorage.setItem('video:volume', String(videoEl!.volume));
			localStorage.setItem('video:muted', String(videoEl!.muted));
		}
		videoEl.addEventListener('volumechange', onVolumeChange);
		return () => videoEl?.removeEventListener('volumechange', onVolumeChange);
	});
</script>

<div class="viewer">
	{#if isVideo}
		<!-- svelte-ignore a11y_media_has_caption -->
		<video
			bind:this={videoEl}
			src={imageFileUrl(hash)}
			poster={thumbUrl(hash)}
			{loop}
			preload="metadata"
			controls
			playsinline
			onloadeddata={() => (loaded = true)}
			onerror={() => (loaded = true)}
			style="max-width: 100%; max-height: 100%; object-fit: contain;"
		></video>
	{:else}
		<img
			src={imageFileUrl(hash)}
			alt={filename}
			onload={() => (loaded = true)}
			onerror={() => (loaded = true)}
			style="max-width: 100%; max-height: 100%; object-fit: contain;"
		/>
	{/if}
	{#if !loaded}
		<div class="loading-spinner" aria-label="Loading"></div>
	{/if}
</div>

<style>
	.viewer {
		position: relative;
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		background: #000;
		min-height: 0;
	}

	.loading-spinner {
		position: absolute;
		top: 50%;
		left: 50%;
		width: 36px;
		height: 36px;
		margin: -18px 0 0 -18px;
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
</style>
