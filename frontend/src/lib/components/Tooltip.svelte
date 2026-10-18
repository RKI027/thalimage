<script lang="ts">
	import type { Snippet } from 'svelte';
	import { placeTooltip, tooltipReaction, type TooltipEvent } from '$lib/tooltip';

	/**
	 * Shows `text` next to its content while the content is hovered or
	 * focused; on a touchscreen, a tap on the content toggles it. With
	 * `fill`, the content takes the width it is given, rather than its own.
	 */
	let { text, fill = false, children }: { text: string; fill?: boolean; children: Snippet } = $props();

	const id = $props.id();
	let open = $state(false);
	let anchor: HTMLElement | undefined = $state();
	let tip: HTMLElement | undefined = $state();
	let position: { left: number; top: number } | null = $state(null);

	// The pointer that started the latest press: a click carries no reliable pointerType.
	let pressedWith = 'mouse';

	function react(event: TooltipEvent, dom?: Event) {
		const next = tooltipReaction(open, event);
		if (next.consume) {
			dom?.preventDefault();
			dom?.stopPropagation();
		}
		open = next.open;
		if (!open) position = null;
	}

	function pressAnywhere(e: PointerEvent) {
		if (open && !anchor?.contains(e.target as Node)) react({ kind: 'outside' });
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

<svelte:window
	onscrollcapture={() => open && react({ kind: 'dismiss' })}
	onkeydown={(e) => e.key === 'Escape' && open && react({ kind: 'dismiss' })}
	onpointerdowncapture={pressAnywhere}
/>

<span
	class="anchor"
	class:fill
	bind:this={anchor}
	aria-describedby={open ? id : undefined}
	onpointerenter={(e) => react({ kind: 'enter', pointer: e.pointerType })}
	onpointerleave={(e) => react({ kind: 'leave', pointer: e.pointerType })}
	onpointerdown={(e) => (pressedWith = e.pointerType)}
	onclick={(e) => react({ kind: 'tap', pointer: pressedWith }, e)}
	onfocusin={() => react({ kind: 'focus' })}
	onfocusout={() => react({ kind: 'blur' })}
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

	.anchor.fill {
		display: flex;
		min-width: 0;
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
		overflow-wrap: anywhere;
		pointer-events: none;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
	}
</style>
