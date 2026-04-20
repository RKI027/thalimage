<script lang="ts">
	import { page } from '$app/stores';
	import { goto, beforeNavigate } from '$app/navigation';
	import { getImage, listImages, archiveImage } from '$lib/api';
	import { browsingContext, backDestination, backLabel } from '$lib/browsingContext';
	import type { ImageDetail, ImageSummary, MetadataMode, OverlayMode } from '$lib/types';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import { attachSwipe } from '$lib/swipe';
	import ImageViewer from '$lib/components/ImageViewer.svelte';
	import MetadataPanel from '$lib/components/MetadataPanel.svelte';
	import SlideshowOverlay from '$lib/components/SlideshowOverlay.svelte';

	let image = $state<ImageDetail | null>(null);
	let neighbors: ImageSummary[] = $state([]);
	let currentIndex = $state(-1);
	let error: string | null = $state(null);
	let pageEl: HTMLElement | null = $state(null);
	let bodyEl: HTMLElement | null = $state(null);
	let sheetEl: HTMLElement | null = $state(null);
	let sheetHandleEl: HTMLElement | null = $state(null);

	let bottomSheetOpen = $state(false);
	let topBarVisible = $state(false);
	let topBarTimer: ReturnType<typeof setTimeout> | null = null;
	let videoLoop = $state(localStorage.getItem('video:loop') === 'true');

	const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);
	const isVideo = $derived(
		image !== null &&
		VIDEO_EXTENSIONS.has(image.filename.slice(image.filename.lastIndexOf('.')).toLowerCase())
	);

	$effect(() => { localStorage.setItem('video:loop', String(videoLoop)); });

	const metadataModes: MetadataMode[] = ['hidden', 'compact', 'full'];
	const overlayModes: OverlayMode[] = ['none', 'minimal', 'full'];

	const ctx = $derived($browsingContext);
	const back = $derived(backDestination(ctx));
	const backText = $derived(backLabel(ctx));
	const inSlideshow = $derived(slideshowStore.status !== 'idle');

	function showTopBar() {
		topBarVisible = true;
		if (topBarTimer) clearTimeout(topBarTimer);
		topBarTimer = setTimeout(() => (topBarVisible = false), 3000);
	}

	function handleTap() {
		if (bottomSheetOpen) {
			bottomSheetOpen = false;
			return;
		}
		showTopBar();
	}

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
			if (ctx.filters) params.filters = ctx.filters;
		}
		const pg = await listImages(params);
		neighbors = pg.items;
		updateIndex();
		if (slideshowStore.consumePendingStart()) {
			enterSlideshow();
		}
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
		if (hash) load(hash);
	});

	$effect(() => {
		const handler = () => {
			slideshowStore.setIsFullscreen(!!document.fullscreenElement);
		};
		document.addEventListener('fullscreenchange', handler);
		return () => document.removeEventListener('fullscreenchange', handler);
	});

	// Swipe navigation on the viewer body (non-slideshow)
	$effect(() => {
		if (!bodyEl || inSlideshow) return;
		return attachSwipe(bodyEl, {
			onSwipeLeft: () => navigate(1),
			onSwipeRight: () => navigate(-1),
			onTap: handleTap
		});
	});

	// Swipe-down to close bottom sheet
	$effect(() => {
		if (!sheetHandleEl || !bottomSheetOpen) return;
		return attachSwipe(sheetHandleEl, { onSwipeDown: () => (bottomSheetOpen = false) }, { threshold: 40 });
	});

	// Cleanup top-bar timer on unmount
	$effect(() => () => {
		if (topBarTimer) clearTimeout(topBarTimer);
	});

	async function toggleArchive() {
		if (!image) return;
		const newState = !image.archived;
		image = await archiveImage(image.content_hash, newState);
		if (newState) {
			// Navigate away from an archived image
			const next = neighbors[currentIndex + 1] ?? neighbors[currentIndex - 1];
			if (next) {
				goto(`/image/${next.content_hash}`);
			} else {
				goto(back);
			}
		}
	}
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
				loop={videoLoop}
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
			<div class="top-bar" class:visible={topBarVisible}>
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
					{#if isVideo}
						<button
							class="loop-btn"
							class:active={videoLoop}
							onclick={() => (videoLoop = !videoLoop)}
							title="Toggle loop"
						>⟲ Loop</button>
					{/if}
					<button
						class="archive-btn"
						class:archived={image.archived}
						onclick={toggleArchive}
						title={image.archived ? 'Unarchive' : 'Archive'}
					>{image.archived ? '↩ Unarchive' : '⬜ Archive'}</button>
				</div>
				<!-- Mobile-only: counter + action buttons -->
				<span class="mobile-counter">
					{#if currentIndex >= 0}{currentIndex + 1} / {neighbors.length}{/if}
				</span>
				<div class="mobile-actions">
					{#if isVideo}
						<button
							class="mobile-btn"
							class:active={videoLoop}
							onclick={() => (videoLoop = !videoLoop)}
							title="Toggle loop"
						>⟲</button>
					{:else}
						<button class="mobile-btn" onclick={enterSlideshow} disabled={neighbors.length === 0} title="Start slideshow">▶</button>
					{/if}
					<button
						class="mobile-btn"
						class:active={image.archived}
						onclick={toggleArchive}
						title={image.archived ? 'Unarchive' : 'Archive'}
					>{image.archived ? '↩' : '⬜'}</button>
					<button class="mobile-btn" onclick={() => { bottomSheetOpen = true; showTopBar(); }} title="Image info">ℹ</button>
				</div>
			</div>

			<!-- body: desktop flex row; mobile full-screen -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="body" bind:this={bodyEl} style="touch-action: pan-y">
				<ImageViewer
					hash={image.content_hash}
					filename={image.filename}
					width={image.width}
					height={image.height}
					loop={videoLoop}
				/>
				<!-- Desktop: metadata side panel. Hidden on mobile via CSS. -->
				<div class="metadata-side">
					<MetadataPanel {image} mode={slideshowStore.metadataMode} />
				</div>
			</div>

			<!-- Mobile bottom sheet -->
			{#if bottomSheetOpen}
				<button class="sheet-backdrop" onclick={() => (bottomSheetOpen = false)} aria-label="Close metadata"></button>
				<div class="bottom-sheet" bind:this={sheetEl}>
					<div class="sheet-handle-area" bind:this={sheetHandleEl}>
						<div class="sheet-handle"></div>
					</div>
					<MetadataPanel {image} mode="full" />
				</div>
			{/if}
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

	.loop-btn {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #888;
		cursor: pointer;
	}

	.loop-btn.active {
		border-color: #6ea8fe;
		color: #6ea8fe;
	}

	.loop-btn:hover {
		background: #3a3a3a;
	}

	.archive-btn {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #888;
		cursor: pointer;
	}

	.archive-btn.archived {
		border-color: #f6a84b;
		color: #f6a84b;
	}

	.archive-btn:hover {
		background: #3a3a3a;
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

	/* metadata-side passes display through to the panel */
	.metadata-side {
		display: contents;
	}

	/* Mobile-only elements hidden on desktop */
	.mobile-counter {
		display: none;
	}

	.mobile-actions {
		display: none;
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

	@media (max-width: 768px) {
		/* top-bar becomes a transparent overlay that fades in on tap */
		.top-bar {
			position: absolute;
			top: 0;
			left: 0;
			right: 0;
			z-index: 10;
			opacity: 0;
			pointer-events: none;
			background: linear-gradient(rgba(0, 0, 0, 0.7), transparent);
			border-bottom: none;
			transition: opacity 0.4s;
		}

		.top-bar.visible {
			opacity: 1;
			pointer-events: auto;
		}

		/* Hide desktop controls and filename on mobile */
		.nav-buttons {
			display: none;
		}

		.filename {
			display: none;
		}

		/* Show mobile-only elements */
		.mobile-counter {
			display: block;
			color: #ddd;
			font-size: 0.85rem;
		}

		.mobile-actions {
			display: flex;
			gap: 8px;
		}

		.mobile-btn {
			display: flex;
			align-items: center;
			justify-content: center;
			background: rgba(255, 255, 255, 0.15);
			border: 1px solid rgba(255, 255, 255, 0.3);
			border-radius: 4px;
			color: #fff;
			cursor: pointer;
			font-size: 1rem;
			padding: 4px 10px;
			min-height: 44px;
			min-width: 44px;
		}

		.mobile-btn:disabled {
			opacity: 0.4;
		}

		.mobile-btn.active {
			border-color: #6ea8fe;
			color: #6ea8fe;
		}

		/* body fills the full image-page area */
		.body {
			position: absolute;
			inset: 0;
		}

		/* hide desktop side panel */
		.metadata-side {
			display: none;
		}

		/* bottom sheet backdrop */
		.sheet-backdrop {
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, 0.4);
			z-index: 50;
		}

		/* bottom sheet */
		.bottom-sheet {
			position: fixed;
			left: 0;
			right: 0;
			bottom: 0;
			height: 60%;
			background: #1a1a1a;
			border-top: 1px solid #444;
			border-radius: 16px 16px 0 0;
			z-index: 60;
			display: flex;
			flex-direction: column;
			overflow: hidden;
			animation: sheet-up 0.25s ease;
		}

		@keyframes sheet-up {
			from {
				transform: translateY(100%);
			}
			to {
				transform: translateY(0);
			}
		}

		.sheet-handle-area {
			padding: 12px 0 8px;
			flex-shrink: 0;
			touch-action: none;
			cursor: grab;
		}

		.sheet-handle {
			width: 40px;
			height: 4px;
			background: #555;
			border-radius: 2px;
			margin: 0 auto;
		}
	}
</style>
