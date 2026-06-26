<script lang="ts">
	import type { Snippet } from 'svelte';
	import { attachSwipe } from '$lib/swipe';

	interface Props {
		open: boolean;
		onclose: () => void;
		children: Snippet;
	}

	let { open, onclose, children }: Props = $props();

	let sheetHandleEl: HTMLElement | null = $state(null);
	let contentEl: HTMLElement | null = $state(null);

	$effect(() => {
		if (!sheetHandleEl || !open) return;
		return attachSwipe(sheetHandleEl, { onSwipeDown: onclose }, { threshold: 40 });
	});

	// iOS Safari chains touch scrolling to whatever scrollable element sits behind
	// a fixed sheet, so dragging the menu scrolls the gallery instead. While the
	// sheet is open, only let the browser handle a touch move when it lands inside
	// the sheet's own scroll area AND that area can actually move in the gesture's
	// direction. Everything else (touch outside, a menu that fits, or overscroll
	// past an edge) is blocked so it can't reach the gallery behind.
	$effect(() => {
		if (!open) return;
		let startY = 0;
		function onTouchStart(e: TouchEvent) {
			startY = e.touches[0]?.clientY ?? 0;
		}
		function onTouchMove(e: TouchEvent) {
			const c = contentEl;
			let inContent = false;
			for (let node = e.target as Node | null; node; node = node.parentNode) {
				if (node === c) {
					inContent = true;
					break;
				}
			}
			if (!inContent || !c || c.scrollHeight <= c.clientHeight) {
				e.preventDefault();
				return;
			}
			const dy = (e.touches[0]?.clientY ?? startY) - startY;
			const atTop = c.scrollTop <= 0;
			const atBottom = c.scrollTop + c.clientHeight >= c.scrollHeight;
			if ((atTop && dy > 0) || (atBottom && dy < 0)) {
				e.preventDefault();
			}
		}
		document.addEventListener('touchstart', onTouchStart, { passive: true });
		document.addEventListener('touchmove', onTouchMove, { passive: false });
		return () => {
			document.removeEventListener('touchstart', onTouchStart);
			document.removeEventListener('touchmove', onTouchMove);
		};
	});
</script>

{#if open}
	<button class="sheet-backdrop" onclick={onclose} aria-label="Close menu"></button>
	<div class="options-sheet">
		<div class="sheet-handle-area" bind:this={sheetHandleEl}>
			<div class="sheet-handle"></div>
		</div>
		<div class="sheet-content" bind:this={contentEl}>
			{@render children()}
		</div>
	</div>
{/if}

<style>
	.sheet-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 50;
		border: none;
		cursor: default;
	}

	.options-sheet {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		max-height: 85vh;
		max-height: 85dvh;
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
		from { transform: translateY(100%); }
		to   { transform: translateY(0); }
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

	.sheet-content {
		padding: 8px 16px max(24px, env(safe-area-inset-bottom, 24px));
		overflow-y: auto;
		overscroll-behavior: contain;
		-webkit-overflow-scrolling: touch;
		touch-action: pan-y;
		flex: 1;
		min-height: 0;
	}

	@media (max-width: 768px) {
		.options-sheet :global(.thumb-slider) {
			width: 100%;
		}

		.options-sheet :global(input[type='range']) {
			width: 100%;
		}
	}
</style>
