<script lang="ts">
	import { page } from '$app/stores';
	import { goto, beforeNavigate } from '$app/navigation';
	import { getImage, listImages } from '$lib/api';
	import { browsingContext, backDestination, backLabel } from '$lib/browsingContext';
	import type { ImageDetail, ImageSummary, MetadataMode, OverlayMode } from '$lib/types';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import ImageViewer from '$lib/components/ImageViewer.svelte';
	import MetadataPanel from '$lib/components/MetadataPanel.svelte';
	import SlideshowOverlay from '$lib/components/SlideshowOverlay.svelte';

	let image: ImageDetail | null = $state(null);
	let neighbors: ImageSummary[] = $state([]);
	let currentIndex = $state(-1);
	let error: string | null = $state(null);
	let pageEl: HTMLElement | null = $state(null);

	const metadataModes: MetadataMode[] = ['hidden', 'compact', 'full'];
	const overlayModes: OverlayMode[] = ['none', 'minimal', 'full'];

	const ctx = $derived($browsingContext);
	const back = $derived(backDestination(ctx));
	const backText = $derived(backLabel(ctx));
	const inSlideshow = $derived(slideshowStore.status !== 'idle');

	async function load(hash: string) {
		error = null;
		try {
			image = await getImage(hash);
			if (neighbors.length === 0) {
				await loadNeighbors();
			} else {
				updateIndex();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load image';
			image = null;
		}
	}

	async function loadNeighbors() {
		if (!ctx) {
			neighbors = [];
			return;
		}
		const params: Parameters<typeof listImages>[0] = { limit: 1000 };
		if (ctx.type === 'collection') {
			params.collection_id = ctx.collectionId;
		}
		const pg = await listImages(params);
		neighbors = pg.items;
		updateIndex();
	}

	function updateIndex() {
		if (!image) return;
		currentIndex = neighbors.findIndex((n) => n.content_hash === image!.content_hash);
		if (inSlideshow) {
			slideshowStore.updateCurrentIndex(currentIndex);
		}
	}

	function navigate(delta: number) {
		const newIndex = currentIndex + delta;
		if (newIndex >= 0 && newIndex < neighbors.length) {
			if (inSlideshow) slideshowStore.resetTimer();
			goto(`/image/${neighbors[newIndex].content_hash}`);
		}
	}

	function enterSlideshow() {
		if (neighbors.length === 0) return;
		slideshowStore.enter(neighbors, currentIndex, (hash) => goto(`/image/${hash}`));
	}

	function onKeydown(e: KeyboardEvent) {
		// Don't intercept if focus is in a form element
		const tag = (e.target as HTMLElement).tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA') return;

		if (e.key === 'ArrowLeft') {
			e.preventDefault();
			navigate(-1);
		} else if (e.key === 'ArrowRight') {
			e.preventDefault();
			navigate(1);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			if (inSlideshow) {
				slideshowStore.exit();
			} else {
				goto(back);
			}
		} else if (e.key === 'i') {
			e.preventDefault();
			if (inSlideshow) {
				const idx = overlayModes.indexOf(slideshowStore.overlayMode);
				slideshowStore.setOverlayMode(overlayModes[(idx + 1) % overlayModes.length]);
			} else {
				const idx = metadataModes.indexOf(slideshowStore.metadataMode);
				slideshowStore.setMetadataMode(metadataModes[(idx + 1) % metadataModes.length]);
			}
		} else if (e.key === ' ') {
			e.preventDefault();
			if (inSlideshow) {
				slideshowStore.togglePlay();
			} else {
				enterSlideshow();
			}
		} else if (e.key === 'f' && inSlideshow) {
			e.preventDefault();
			if (pageEl) slideshowStore.toggleFullscreen(pageEl);
		} else if (e.key === 's' && inSlideshow) {
			e.preventDefault();
			slideshowStore.toggleShuffle();
		}
	}

	beforeNavigate(({ to }) => {
		if (!to?.url.pathname.startsWith('/image/')) {
			slideshowStore.exit();
		}
	});

	$effect(() => {
		const hash = $page.params.hash;
		if (hash) {
			load(hash);
		}
	});

	$effect(() => {
		const handler = () => {
			slideshowStore.setIsFullscreen(!!document.fullscreenElement);
		};
		document.addEventListener('fullscreenchange', handler);
		return () => document.removeEventListener('fullscreenchange', handler);
	});
</script>

<svelte:window onkeydown={onKeydown} />

{#if error}
	<div class="error">{error}</div>
{:else if image}
	{#if inSlideshow}
		<div class="image-page" bind:this={pageEl}>
			<ImageViewer
				hash={image.content_hash}
				filename={image.filename}
				width={image.width}
				height={image.height}
			/>
			<SlideshowOverlay
				{image}
				{currentIndex}
				total={neighbors.length}
				status={slideshowStore.status}
				config={slideshowStore.config}
				isFullscreen={slideshowStore.isFullscreen}
				overlayMode={slideshowStore.overlayMode}
				onPrev={() => navigate(-1)}
				onNext={() => navigate(1)}
				onExit={() => slideshowStore.exit()}
				onTogglePlay={() => slideshowStore.togglePlay()}
				onToggleShuffle={() => slideshowStore.toggleShuffle()}
				onToggleFullscreen={() => pageEl && slideshowStore.toggleFullscreen(pageEl)}
				onOverlayModeChange={(m) => slideshowStore.setOverlayMode(m)}
			/>
		</div>
	{:else}
		<div class="image-page" bind:this={pageEl}>
			<div class="top-bar">
				<a href={back}>{backText}</a>
				<span class="filename">{image.filename}</span>
				<div class="nav-buttons">
					<button disabled={currentIndex <= 0} onclick={() => navigate(-1)}>← Prev</button>
					<span class="position">
						{#if currentIndex >= 0}
							{currentIndex + 1} / {neighbors.length}
						{/if}
					</span>
					<button
						disabled={currentIndex < 0 || currentIndex >= neighbors.length - 1}
						onclick={() => navigate(1)}
					>
						Next →
					</button>
					<button onclick={enterSlideshow} title="Start slideshow (Space)" disabled={neighbors.length === 0}>
						▶ Slideshow
					</button>
				</div>
			</div>
			<div class="body">
				<ImageViewer
					hash={image.content_hash}
					filename={image.filename}
					width={image.width}
					height={image.height}
				/>
				<MetadataPanel {image} mode={slideshowStore.metadataMode} />
			</div>
		</div>
	{/if}
{:else}
	<div class="loading">Loading…</div>
{/if}

<style>
	.image-page {
		display: flex;
		flex-direction: column;
		height: 100%;
		position: relative;
	}

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.filename {
		color: #ccc;
		font-size: 0.9rem;
	}

	.nav-buttons {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.nav-buttons button {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
	}

	.nav-buttons button:hover:not(:disabled) {
		background: #3a3a3a;
	}

	.nav-buttons button:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.position {
		color: #888;
		font-size: 0.85rem;
		min-width: 60px;
		text-align: center;
	}

	.body {
		flex: 1;
		display: flex;
		min-height: 0;
	}

	.error {
		padding: 32px;
		text-align: center;
		color: #f66;
	}

	.loading {
		padding: 32px;
		text-align: center;
		color: #888;
	}
</style>
