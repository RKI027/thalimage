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

	$effect(() => {
		if (!overlayEl) return;
		return attachSwipe(overlayEl, {
			onSwipeLeft: onNext,
			onSwipeRight: onPrev,
			onTap: resetFadeTimer
		});
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="slideshow-overlay"
	bind:this={overlayEl}
	onpointermove={resetFadeTimer}
	onpointerdown={resetFadeTimer}
>
	<!-- Controls bar -->
	<div class="controls" class:visible={controlsVisible}>
		<button class="ctrl-btn" onclick={onExit} title="Exit slideshow (Escape)">✕</button>
		<button class="ctrl-btn" onclick={onTogglePlay} title="Play/Pause (Space)">
			{status === 'playing' ? '⏸' : '▶'}
		</button>
		<button class="ctrl-btn" class:active={config.shuffle} onclick={onToggleShuffle} title="Shuffle (s)">
			⇄
		</button>
		<span class="counter">{currentIndex + 1} / {total}</span>
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

	<!-- Click zones for prev/next -->
	<button class="zone left" onclick={onPrev} aria-label="Previous image"></button>
	<button class="zone right" onclick={onNext} aria-label="Next image"></button>
</div>

<style>
	.slideshow-overlay {
		position: fixed;
		inset: 0;
		z-index: 100;
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
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 16px;
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

	.zone {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 30%;
		background: transparent;
		border: none;
		cursor: pointer;
		pointer-events: auto;
		opacity: 0;
	}

	.zone.left {
		left: 0;
		cursor: w-resize;
	}

	.zone.right {
		right: 0;
		cursor: e-resize;
	}
</style>
