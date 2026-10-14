<script lang="ts">
	import type { Snippet } from 'svelte';
	import { placeTooltip } from '$lib/tooltip';

	/** Shows `text` next to its content while the content is hovered or focused. */
	let { text, children }: { text: string; children: Snippet } = $props();

	const id = $props.id();
	let open = $state(false);
	let anchor: HTMLElement | undefined = $state();
	let tip: HTMLElement | undefined = $state();
	let position: { left: number; top: number } | null = $state(null);

	function show() {
		open = true;
	}

	function hide() {
		open = false;
		position = null;
	}

	$effect(() => {
		if (!open || !anchor || !tip) return;
		position = placeTooltip(anchor.getBoundingClientRect(), tip.getBoundingClientRect(), {
			width: window.innerWidth,
			height: window.innerHeight
		});
	});

	/** Renders the tip under <body>, so no ancestor's overflow or transform can clip or shift it. */
	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return { destroy: () => node.remove() };
	}
</script>

<svelte:window onscroll={hide} onkeydown={(e) => e.key === 'Escape' && hide()} />

<span
	class="anchor"
	bind:this={anchor}
	aria-describedby={open ? id : undefined}
	onmouseenter={show}
	onmouseleave={hide}
	onfocusin={show}
	onfocusout={hide}
	role="presentation"
>
	{@render children()}
</span>

{#if open}
	<div
		{id}
		role="tooltip"
		class="tooltip"
		use:portal
		bind:this={tip}
		style:left="{position?.left ?? 0}px"
		style:top="{position?.top ?? 0}px"
		style:visibility={position ? 'visible' : 'hidden'}
	>
		{text}
	</div>
{/if}

<style>
	.anchor {
		display: inline-flex;
	}

	.tooltip {
		position: fixed;
		z-index: 1000;
		max-width: 260px;
		padding: 5px 8px;
		border-radius: 4px;
		background: #111;
		border: 1px solid #444;
		color: #ddd;
		font-size: 0.75rem;
		line-height: 1.3;
		pointer-events: none;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
	}
</style>
