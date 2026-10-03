<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto, beforeNavigate } from '$app/navigation';
	import { getImage, getNeighbors, archiveImage, previewUrl, getEloRankings } from '$lib/api';
	import { browsingContext, backDestination, backLabel, contextListing } from '$lib/browsingContext';
	import { settingsStore } from '$lib/stores';
	import type { ImageDetail, ImageSummary, MetadataMode, OverlayMode } from '$lib/types';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import { attachSwipe } from '$lib/swipe';
	import { readStored, writeStored } from '$lib/storage';
	import Icon from '$lib/components/Icon.svelte';
	import ImageViewer from '$lib/components/ImageViewer.svelte';
	import MetadataPanel from '$lib/components/MetadataPanel.svelte';
	import SlideshowOverlay from '$lib/components/SlideshowOverlay.svelte';

	let image = $state<ImageDetail | null>(null);
	// A window of the browsing context's listing around the current image.
	let neighbors: ImageSummary[] = $state([]);
	let currentIndex = $state(-1);
	// Listing position of neighbors[0], and the listing's size.
	let windowStart = $state(0);
	let total = $state(0);
	const position = $derived(currentIndex >= 0 ? windowStart + currentIndex : -1);
	// Bumped per load; a response for an earlier load is dropped, so the page
	// never shows an image the URL has already moved past.
	let loadSeq = 0;
	let error: string | null = $state(null);
	let pageEl: HTMLElement | null = $state(null);
	let bodyEl: HTMLElement | null = $state(null);
	let sheetEl: HTMLElement | null = $state(null);
	let sheetHandleEl: HTMLElement | null = $state(null);

	let videoEl = $state<HTMLVideoElement | null>(null);
	let videoPlaying = $state(false);
	let videoMuted = $state(false);
	let bottomSheetOpen = $state(false);
	let topBarVisible = $state(false);
	let topBarTimer: ReturnType<typeof setTimeout> | null = null;
	let videoLoop = $state(readStored('video:loop', false));

	// Neighbours fetched on each side of the current image; the slideshow walks
	// that window. A new window is fetched once navigation comes within
	// WINDOW_EDGE of either end (unless that end is the listing's own).
	const WINDOW = 500;
	const WINDOW_EDGE = 50;
	// ELO scores fetched for weighting the slideshow: enough for a whole window.
	const NEIGHBOR_LIMIT = 2 * WINDOW + 1;

	const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);
	const isVideo = $derived(
		image !== null &&
		VIDEO_EXTENSIONS.has(image.filename.slice(image.filename.lastIndexOf('.')).toLowerCase())
	);

	$effect(() => { writeStored('video:loop', videoLoop); });

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
		const seq = ++loadSeq;
		error = null;
		try {
			const loaded = await getImage(hash);
			if (seq !== loadSeq) return;
			image = loaded;
			const idx = neighbors.findIndex((n) => n.content_hash === hash);
			if (idx >= 0) {
				setIndex(idx);
				// The slideshow walks the window it started with.
				if (!inSlideshow && !windowCovers(idx)) refreshWindow(loaded);
			} else {
				await refreshWindow(loaded, true);
			}
		} catch (e) {
			if (seq !== loadSeq) return;
			error = e instanceof Error ? e.message : 'Failed to load image';
			image = null;
		}
	}

	// Whether the window reaches far enough past idx on both sides (or to
	// the listing's own ends) that no refetch is needed yet.
	function windowCovers(idx: number): boolean {
		const atListingStart = windowStart === 0;
		const atListingEnd = windowStart + neighbors.length >= total;
		return (
			(idx >= WINDOW_EDGE || atListingStart) &&
			(neighbors.length - 1 - idx >= WINDOW_EDGE || atListingEnd)
		);
	}

	let windowInFlight = false;

	/** Fetch the window around `around`. Runs one at a time unless forced
	 * (the image shown is outside the current window). */
	async function refreshWindow(around: ImageSummary, force = false) {
		if (!ctx) {
			neighbors = [];
			setIndex(-1);
			return;
		}
		if (windowInFlight && !force) return;
		windowInFlight = true;
		try {
			const nb = await getNeighbors(around.content_hash, {
				...contextListing(ctx, $settingsStore.show_nsfw),
				window: WINDOW
			});
			const fetched = [...nb.before, around, ...nb.after];
			// Navigation may have moved on meanwhile; the window is still worth
			// having as long as the image now shown is in it.
			const idx = fetched.findIndex((n) => n.content_hash === $page.params.hash);
			if (idx < 0) return;
			neighbors = fetched;
			windowStart = nb.position - nb.before.length;
			total = nb.total_count;
			setIndex(idx);
			if (slideshowStore.consumePendingStart()) {
				enterSlideshow();
			}
		} finally {
			windowInFlight = false;
		}
	}

	function setIndex(idx: number) {
		currentIndex = idx;
		if (inSlideshow) {
			slideshowStore.updateCurrentIndex(idx);
		}
	}

	function navigate(delta: number) {
		if (inSlideshow) slideshowStore.resetTimer();
		// In a shuffle slideshow, ←/→ walk the shuffle order/history (matching
		// auto-advance) instead of the underlying collection order.
		if (inSlideshow && slideshowStore.isShuffle) {
			if (delta < 0) slideshowStore.back();
			else slideshowStore.advance();
			return;
		}
		const newIndex = currentIndex + delta;
		if (newIndex >= 0 && newIndex < neighbors.length) {
			// Move now rather than when the image arrives, so a second press
			// during a slow load steps on from here instead of repeating.
			setIndex(newIndex);
			const target = neighbors[newIndex];
			if (!windowCovers(newIndex)) refreshWindow(target);
			goto(`/image/${target.content_hash}`);
		}
	}

	async function enterSlideshow() {
		if (neighbors.length === 0) return;
		// ELO weighting needs a collection context (scores are per-collection).
		// "All Images" has no collection row, so ELO is unavailable there.
		let eloScores: Map<string, number> | null = null;
		let eloAvailable = false;
		if (ctx?.type === 'collection') {
			eloAvailable = true;
			try {
				const rankings = await getEloRankings(ctx.collectionId!, NEIGHBOR_LIMIT);
				eloScores = new Map(rankings.map((r) => [r.content_hash, r.score]));
			} catch {
				// No scores yet — defaults to uniform (all 1500).
				eloScores = new Map();
			}
		}
		slideshowStore.enter(neighbors, currentIndex, (hash) => goto(`/image/${hash}`), {
			eloScores,
			eloAvailable
		});
	}

	function toggleVideoPlayback() {
		const v = videoEl;
		if (!v) return;
		if (v.paused) v.play().catch(() => {});
		else v.pause();
	}

	function toggleVideoMute() {
		if (videoEl) videoEl.muted = !videoEl.muted;
	}

	// Mirror the video element's playback/mute state so the custom controls
	// (which replace the native chrome) can reflect and toggle it.
	$effect(() => {
		const v = videoEl;
		if (!v) return;
		const sync = () => {
			videoPlaying = !v.paused;
			videoMuted = v.muted;
		};
		sync();
		v.addEventListener('play', sync);
		v.addEventListener('pause', sync);
		v.addEventListener('volumechange', sync);
		return () => {
			v.removeEventListener('play', sync);
			v.removeEventListener('pause', sync);
			v.removeEventListener('volumechange', sync);
		};
	});

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
		} else if (e.key === 'e' && inSlideshow) {
			e.preventDefault();
			slideshowStore.toggleWeighted();
		} else if (e.key === 'k' && isVideo) {
			e.preventDefault();
			toggleVideoPlayback();
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

	// Slideshow video playback: autoplay once, advance when it ends.
	$effect(() => {
		const v = videoEl;
		// Re-run on each slide so a new video autoplays.
		const _hash = image?.content_hash;
		if (!inSlideshow || !isVideo || !v) return;

		const onEnded = () => {
			if (slideshowStore.status === 'playing') slideshowStore.advance();
		};
		v.addEventListener('ended', onEnded);

		if (untrack(() => slideshowStore.status) === 'playing') {
			v.play().catch(() => {});
		}

		return () => v.removeEventListener('ended', onEnded);
	});

	// Slideshow timer vs. video: hold the timer while a video plays; on image
	// slides keep the interval running.
	$effect(() => {
		if (!inSlideshow) return;
		const playing = slideshowStore.status === 'playing';
		const _hash = image?.content_hash;
		if (!playing) return;
		if (isVideo) {
			if (videoEl?.ended) {
				// Resumed after the video finished while paused — move on.
				slideshowStore.advance();
			} else {
				slideshowStore.suspendTimer();
			}
		} else {
			slideshowStore.resetTimer();
		}
	});

	// Preload nearby images so manual navigation and slideshow advance are
	// instant and don't eat into the slideshow timer. Videos are skipped — their
	// full files are too large to prefetch eagerly.
	$effect(() => {
		const idx = currentIndex;
		if (idx < 0 || neighbors.length === 0) return;
		for (const offset of [1, 2, -1]) {
			const n = neighbors[idx + offset];
			if (!n) continue;
			const ext = n.filename.slice(n.filename.lastIndexOf('.')).toLowerCase();
			if (VIDEO_EXTENSIONS.has(ext)) continue;
			const img = new Image();
			img.src = previewUrl(n.content_hash);
		}
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
			// Navigate away from an archived image, and drop the window it was
			// part of: the listing no longer includes it.
			const next = neighbors[currentIndex + 1] ?? neighbors[currentIndex - 1];
			neighbors = [];
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
				loop={false}
				nativeControls={false}
				bind:videoEl
			/>
			<SlideshowOverlay
				{image}
				currentIndex={position}
				{total}
				status={slideshowStore.status}
				config={slideshowStore.config}
				isFullscreen={slideshowStore.isFullscreen}
				{isVideo}
				{videoPlaying}
				{videoMuted}
				eloAvailable={slideshowStore.eloAvailable}
				overlayMode={slideshowStore.overlayMode}
				onPrev={() => navigate(-1)}
				onNext={() => navigate(1)}
				onExit={() => slideshowStore.exit()}
				onTogglePlay={() => slideshowStore.togglePlay()}
				onToggleVideo={toggleVideoPlayback}
				onToggleMute={toggleVideoMute}
				onToggleShuffle={() => slideshowStore.toggleShuffle()}
				onToggleWeighted={() => slideshowStore.toggleWeighted()}
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
					<button class="control" disabled={currentIndex <= 0} onclick={() => navigate(-1)}>← Prev</button>
					<span class="position">
						{#if currentIndex >= 0}
							{position + 1} / {total}
						{/if}
					</span>
					<button
						class="control"
						disabled={currentIndex < 0 || currentIndex >= neighbors.length - 1}
						onclick={() => navigate(1)}
					>
						Next →
					</button>
					<button class="control" onclick={enterSlideshow} title="Start slideshow (Space)" disabled={neighbors.length === 0}>
						Slideshow
					</button>
					{#if isVideo}
						<button
							class="control loop-btn"
							class:active={videoLoop}
							onclick={() => (videoLoop = !videoLoop)}
							title="Toggle loop"
						>⟲ Loop</button>
					{/if}
					<button
						class="control archive-btn"
						class:archived={image.archived}
						onclick={toggleArchive}
						title={image.archived ? 'Unarchive' : 'Archive'}
					>{image.archived ? '↩ Unarchive' : '⬜ Archive'}</button>
				</div>
				<!-- Mobile-only: counter + action buttons -->
				<span class="mobile-counter">
					{#if currentIndex >= 0}{position + 1} / {total}{/if}
				</span>
				<div class="mobile-actions">
					{#if isVideo}
						<button
							class="mobile-btn"
							class:active={videoLoop}
							onclick={() => (videoLoop = !videoLoop)}
							title="Toggle loop"
						>
							<Icon name="loop" />
							<span class="mobile-btn-label">Loop</span>
						</button>
					{:else}
						<button class="mobile-btn" onclick={enterSlideshow} disabled={neighbors.length === 0} title="Start slideshow">
							<Icon name="play" />
							<span class="mobile-btn-label">Slides</span>
						</button>
					{/if}
					<button
						class="mobile-btn"
						class:active={image.archived}
						onclick={toggleArchive}
						title={image.archived ? 'Unarchive' : 'Archive'}
					>
						<Icon name={image.archived ? 'unarchive' : 'archive'} />
						<span class="mobile-btn-label">{image.archived ? 'Restore' : 'Archive'}</span>
					</button>
					<button class="mobile-btn" onclick={() => { bottomSheetOpen = true; showTopBar(); }} title="Image info">
						<Icon name="info" />
						<span class="mobile-btn-label">Info</span>
					</button>
				</div>
			</div>

			<!-- body: desktop flex row; mobile full-screen -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="body" bind:this={bodyEl} style="touch-action: none">
				<ImageViewer
					hash={image.content_hash}
					filename={image.filename}
					width={image.width}
					height={image.height}
					loop={videoLoop}
					nativeControls={false}
					bind:videoEl
				/>
				<!-- Desktop: metadata side panel. Hidden on mobile via CSS. -->
				<div class="metadata-side">
					<MetadataPanel {image} mode={slideshowStore.metadataMode} />
				</div>
			</div>

			<!-- Video playback controls, bottom-centered -->
			{#if isVideo}
				<div class="video-controls" class:visible={topBarVisible}>
					<button class="mobile-btn" onclick={toggleVideoPlayback} title="Play/pause video (k)">
						<Icon name={videoPlaying ? 'pause' : 'play'} />
					</button>
					<button
						class="mobile-btn"
						class:active={videoMuted}
						onclick={toggleVideoMute}
						title="Mute/unmute video"
					>
						<Icon name={videoMuted ? 'mute' : 'volume'} />
					</button>
				</div>
			{/if}

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

	.loop-btn.active {
		border-color: #6ea8fe;
		color: #6ea8fe;
	}

	.archive-btn.archived {
		border-color: #f6a84b;
		color: #f6a84b;
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

	/* Video playback controls, bottom-centered. Always shown on desktop; on
	   mobile they fade with the rest of the chrome (see media query). */
	.video-controls {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		z-index: 10;
		display: flex;
		justify-content: center;
		gap: 8px;
		padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
	}

	.video-controls .mobile-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(255, 255, 255, 0.15);
		border: 1px solid rgba(255, 255, 255, 0.3);
		border-radius: 4px;
		color: #fff;
		cursor: pointer;
		font-size: 1rem;
		padding: 8px 14px;
		min-height: 44px;
		min-width: 44px;
	}

	.video-controls .mobile-btn.active {
		border-color: #6ea8fe;
		color: #6ea8fe;
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
			padding: calc(8px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right))
				8px max(16px, env(safe-area-inset-left));
			background: linear-gradient(rgba(0, 0, 0, 0.7), transparent);
			border-bottom: none;
			transition: opacity 0.4s;
		}

		.top-bar.visible {
			opacity: 1;
			pointer-events: auto;
		}

		/* Bottom video controls fade with the top bar on mobile */
		.video-controls {
			opacity: 0;
			pointer-events: none;
			background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
			transition: opacity 0.4s;
		}

		.video-controls.visible {
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
			flex-direction: column;
			align-items: center;
			justify-content: center;
			gap: 3px;
			background: rgba(255, 255, 255, 0.15);
			border: 1px solid rgba(255, 255, 255, 0.3);
			border-radius: 4px;
			color: #fff;
			cursor: pointer;
			padding: 4px 8px;
			min-height: 44px;
			min-width: 44px;
		}

		.mobile-btn-label {
			font-size: 10px;
			line-height: 1;
			letter-spacing: 0.01em;
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
			padding-bottom: env(safe-area-inset-bottom);
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
