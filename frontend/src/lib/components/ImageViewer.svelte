<script lang="ts">
	import { imageFileUrl, thumbUrl } from '$lib/api';

	const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);

	let {
		hash,
		filename,
		width,
		height,
		loop = false
	}: {
		hash: string;
		filename: string;
		width: number;
		height: number;
		loop?: boolean;
	} = $props();

	const isVideo = $derived(
		VIDEO_EXTENSIONS.has(filename.slice(filename.lastIndexOf('.')).toLowerCase())
	);

	let videoEl = $state<HTMLVideoElement | null>(null);

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
			style="max-width: 100%; max-height: 100%; object-fit: contain;"
		></video>
	{:else}
		<img
			src={imageFileUrl(hash)}
			alt={filename}
			style="max-width: 100%; max-height: 100%; object-fit: contain;"
		/>
	{/if}
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
