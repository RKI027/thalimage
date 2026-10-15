<script lang="ts">
	import type * as PlotModule from '@observablehq/plot';

	let {
		plot,
		title,
		note,
		render
	}: {
		/** Observable Plot, loaded by the caller (it is only needed here). */
		plot: typeof PlotModule;
		title: string;
		note?: string;
		/** Draws the chart at the given width. */
		render: (Plot: typeof PlotModule, width: number) => Element;
	} = $props();

	let host: HTMLDivElement | undefined = $state();
	let width = $state(0);

	$effect(() => {
		if (!host || width === 0) return;
		const node = render(plot, width);
		host.replaceChildren(node);
		return () => node.remove();
	});
</script>

<figure>
	<figcaption>
		<span class="title">{title}</span>
		{#if note}<span class="note">{note}</span>{/if}
	</figcaption>
	<div class="plot" bind:this={host} bind:clientWidth={width}></div>
</figure>

<style>
	figure {
		margin: 0;
		padding: 12px 16px 8px;
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		min-width: 0;
	}

	figcaption {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-bottom: 8px;
	}

	.title {
		color: #f0efec;
		font-weight: 600;
		font-size: 0.95rem;
	}

	.note {
		color: #898781;
		font-size: 0.8rem;
	}

	.plot :global(svg) {
		display: block;
		overflow: visible;
	}
</style>
