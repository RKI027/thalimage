<script lang="ts">
	/** Stroked icons drawn inline so they share one weight, size and colour. */
	let { name, size = 20 }: { name: string; size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.8"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	{#if name === 'play'}
		<path d="M7 4.5 19 12 7 19.5Z" />
	{:else if name === 'loop'}
		<path d="M4 9a8 8 0 0 1 14-3" />
		<path d="M20 15a8 8 0 0 1-14 3" />
		<path d="M18 2v5h-5" />
		<path d="M6 22v-5h5" />
	{:else if name === 'archive'}
		<rect x="3" y="4" width="18" height="5" rx="1" />
		<path d="M5 9v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9" />
		<path d="M10 13h4" />
	{:else if name === 'unarchive'}
		<rect x="3" y="4" width="18" height="5" rx="1" />
		<path d="M5 9v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9" />
		<path d="M12 17v-5" />
		<path d="M9.5 14.5 12 12l2.5 2.5" />
	{:else if name === 'pause'}
		<path d="M9 4.5v15" />
		<path d="M15 4.5v15" />
	{:else if name === 'volume'}
		<path d="M11 5 6.5 9H3v6h3.5L11 19Z" />
		<path d="M15.5 9.5a3.5 3.5 0 0 1 0 5" />
		<path d="M18 7a7 7 0 0 1 0 10" />
	{:else if name === 'mute'}
		<path d="M11 5 6.5 9H3v6h3.5L11 19Z" />
		<path d="m16 10 5 4" />
		<path d="m21 10-5 4" />
	{:else if name === 'info'}
		<circle cx="12" cy="12" r="9" />
		<path d="M12 11v5" />
		<path d="M12 7.75v.5" />
	{/if}
</svg>

<style>
	svg {
		display: block;
		flex-shrink: 0;
	}
</style>
