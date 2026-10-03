<script lang="ts">
	import { isVideoFilename } from '$lib/media';
	import { imageFileUrl, previewUrl, thumbUrl } from '$lib/api';
	import { readStored, writeStored } from '$lib/storage';


	let {
		hash,
		filename,
		width,
		height,
		loop = false,
		nativeControls = true,
		videoEl = $bindable(null)
	}: {
		hash: string;
		filename: string;
		width: number;
		height: number;
		loop?: boolean;
		nativeControls?: boolean;
		videoEl?: HTMLVideoElement | null;
	} = $props();

	const isVideo = $derived(isVideoFilename(filename));

	let loaded = $state(false);
	// Reset the loading state whenever the source changes.
	$effect(() => {
		void hash;
		loaded = false;
	});

	$effect(() => {
		if (!videoEl) return;
		videoEl.volume = readStored('video:volume', 1);
		videoEl.muted = readStored('video:muted', false);

		function onVolumeChange() {
			writeStored('video:volume', videoEl!.volume);
			writeStored('video:muted', videoEl!.muted);
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
			controls={nativeControls}
			playsinline
			onloadeddata={() => (loaded = true)}
			onerror={() => (loaded = true)}
			style="max-width: 100%; max-height: 100%; object-fit: contain;"
		></video>
	{:else}
		<img
			src={previewUrl(hash)}
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
