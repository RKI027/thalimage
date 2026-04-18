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

	$effect(() => {
		if (!sheetHandleEl || !open) return;
		return attachSwipe(sheetHandleEl, { onSwipeDown: onclose }, { threshold: 40 });
	});
</script>

{#if open}
	<button class="sheet-backdrop" onclick={onclose} aria-label="Close menu"></button>
	<div class="options-sheet">
		<div class="sheet-handle-area" bind:this={sheetHandleEl}>
			<div class="sheet-handle"></div>
		</div>
		<div class="sheet-content">
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
