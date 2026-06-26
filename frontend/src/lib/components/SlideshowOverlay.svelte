<script lang="ts">
	import type { ImageDetail, SlideshowStatus, OverlayMode } from '$lib/types';
	import type { SlideshowConfig } from '$lib/slideshowStore.svelte';
	import { attachSwipe } from '$lib/swipe';

	let {
		image,
		currentIndex,
		total,
		status,
		config,
		isFullscreen,
		isVideo,
		overlayMode,
		onPrev,
		onNext,
		onExit,
		onTogglePlay,
		onToggleShuffle,
		onToggleFullscreen,
		onOverlayModeChange
	}: {
		image: ImageDetail;
		currentIndex: number;
		total: number;
		status: SlideshowStatus;
		config: SlideshowConfig;
		isFullscreen: boolean;
		isVideo: boolean;
		overlayMode: OverlayMode;
		onPrev: () => void;
		onNext: () => void;
		onExit: () => void;
		onTogglePlay: () => void;
		onToggleShuffle: () => void;
		onToggleFullscreen: () => void;
		onOverlayModeChange: (mode: OverlayMode) => void;
	} = $props();

	let controlsVisible = $state(true);
	let fadeTimer: ReturnType<typeof setTimeout> | null = null;
	let overlayEl: HTMLElement | null = $state(null);

	const overlayModes: OverlayMode[] = ['none', 'minimal', 'full'];

	function resetFadeTimer() {
		controlsVisible = true;
		if (fadeTimer !== null) clearTimeout(fadeTimer);
		fadeTimer = setTimeout(() => {
			controlsVisible = false;
		}, 3000);
	}

	function toggleControls() {
		if (controlsVisible) {
			controlsVisible = false;
			if (fadeTimer !== null) clearTimeout(fadeTimer);
		} else {
			resetFadeTimer();
		}
	}

	// Reveal controls when a mouse moves (desktop). Touch reveal/hide is handled
	// by the tap handler so a stationary tap can toggle without a stray move event
	// pre-revealing the controls.
	function onPointerMove(e: PointerEvent) {
		if (e.pointerType === 'mouse') resetFadeTimer();
	}

	function cycleOverlayMode() {
		const idx = overlayModes.indexOf(overlayMode);
		onOverlayModeChange(overlayModes[(idx + 1) % overlayModes.length]);
	}

	$effect(() => {
		resetFadeTimer();
		return () => {
			if (fadeTimer !== null) clearTimeout(fadeTimer);
		};
	});

	// Swipe and tap on the image surface. For video slides the native player owns
	// the surface, so navigation goes through the always-visible control bar.
	$effect(() => {
		if (!overlayEl || isVideo) return;
		return attachSwipe(overlayEl, {
			onSwipeLeft: onNext,
			onSwipeRight: onPrev,
			onTap: toggleControls
		});
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="slideshow-overlay"
	class:video={isVideo}
	bind:this={overlayEl}
	onpointermove={onPointerMove}
>
	<!-- Controls bar -->
	<div class="controls" class:visible={controlsVisible || isVideo}>
		<button class="ctrl-btn" onclick={onExit} title="Exit slideshow (Escape)">✕</button>
		<button class="ctrl-btn" onclick={onTogglePlay} title="Play/Pause (Space)">
			{status === 'playing' ? '⏸' : '▶'}
		</button>
		<button class="ctrl-btn" class:active={config.shuffle} onclick={onToggleShuffle} title="Shuffle (s)">
			⇄
		</button>
		<button class="ctrl-btn" onclick={onPrev} title="Previous (←)">‹</button>
		<span class="counter">{currentIndex + 1} / {total}</span>
		<button class="ctrl-btn" onclick={onNext} title="Next (→)">›</button>
		<button class="ctrl-btn" onclick={cycleOverlayMode} title="Cycle metadata overlay (i)">
			{overlayMode === 'none' ? 'ℹ︎' : overlayMode === 'minimal' ? 'ℹ' : '⊞'}
		</button>
		<button class="ctrl-btn" onclick={onToggleFullscreen} title="Fullscreen (f)">
			{isFullscreen ? '⤡' : '⤢'}
		</button>
	</div>

	<!-- Metadata overlay -->
	{#if overlayMode !== 'none'}
		<div class="meta-overlay">
			<span class="meta-filename">{image.filename}</span>
			{#if overlayMode === 'full' && image.prompt}
				<p class="meta-prompt">{image.prompt}</p>
			{/if}
		</div>
	{/if}
</div>

<style>
	.slideshow-overlay {
		position: fixed;
		inset: 0;
		z-index: 100;
		/* Catch tap (toggle controls) and swipe (navigate) across the whole image. */
		pointer-events: auto;
	}

	/* On video slides the native player must stay reachable, so the surface lets
	   pointer events through; navigation uses the always-visible control bar. */
	.slideshow-overlay.video {
		pointer-events: none;
	}

	:global(:fullscreen) .slideshow-overlay {
		position: absolute;
	}

	.controls {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: calc(12px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 12px
			max(16px, env(safe-area-inset-left));
		background: linear-gradient(rgba(0, 0, 0, 0.7), transparent);
		pointer-events: auto;
		opacity: 0;
		transition: opacity 0.4s;
	}

	.controls.visible {
		opacity: 1;
	}

	.ctrl-btn {
		background: rgba(255, 255, 255, 0.15);
		border: 1px solid rgba(255, 255, 255, 0.3);
		border-radius: 4px;
		color: #fff;
		cursor: pointer;
		font-size: 1rem;
		padding: 4px 10px;
		line-height: 1.4;
	}

	.ctrl-btn:hover {
		background: rgba(255, 255, 255, 0.3);
	}

	.ctrl-btn.active {
		background: rgba(100, 180, 255, 0.4);
		border-color: rgba(100, 180, 255, 0.6);
	}

	.counter {
		color: #ddd;
		font-size: 0.85rem;
		flex: 1;
		text-align: center;
	}

	.meta-overlay {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		padding: 48px 24px 16px;
		background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
		pointer-events: none;
	}

	.meta-filename {
		display: block;
		color: #eee;
		font-size: 0.9rem;
		font-weight: 500;
	}

	.meta-prompt {
		margin: 6px 0 0;
		color: #bbb;
		font-size: 0.8rem;
		line-height: 1.4;
		max-height: 4.2em;
		overflow: hidden;
		display: -webkit-box;
		line-clamp: 3;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
	}
</style>
