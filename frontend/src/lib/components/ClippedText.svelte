<script lang="ts">
	import Tooltip from './Tooltip.svelte';

	/**
	 * `text` on one line, cut with an ellipsis when it does not fit, so what
	 * follows never moves; the whole text then shows in a tooltip.
	 */
	let { text }: { text: string } = $props();

	let el: HTMLSpanElement | undefined = $state();
	let clipped = $state(false);

	$effect(() => {
		const span = el;
		if (!span) return;
		const measure = () => (clipped = span.scrollWidth > span.clientWidth);
		measure();
		const observer = new ResizeObserver(measure);
		observer.observe(span);
		return () => observer.disconnect();
	});
</script>

{#if clipped}
	<Tooltip {text} fill>
		<span class="clipped" bind:this={el}>{text}</span>
	</Tooltip>
{:else}
	<span class="clipped" bind:this={el}>{text}</span>
{/if}

<style>
	.clipped {
		display: block;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
