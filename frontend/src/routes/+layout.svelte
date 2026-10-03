<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { settingsHref } from '$lib/settingsLink';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import { mobileStore } from '$lib/mobileStore.svelte';
	import { settingsStore } from '$lib/stores';

	let { children } = $props();

	onMount(() => { settingsStore.refresh(); });

	const isSlideshow = $derived(slideshowStore.status !== 'idle');
	const routeGroup = $derived($page.url.pathname.split('/')[1] || 'home');

	const settingsLink = $derived(settingsHref($page.url));
</script>

<svelte:head>
	<title>Thalimage</title>
</svelte:head>

<div class="app">
	{#if !isSlideshow}
		<header>
			<a href="/" class="logo">Thalimage</a>
			<nav>
				<a href="/">Gallery</a>
				<a href={settingsLink}>Settings</a>
			</nav>
		</header>
	{/if}
	<div class="body">
		{#if !isSlideshow}
			{#if mobileStore.drawerOpen}
				<button
					class="drawer-backdrop"
					onclick={mobileStore.close}
					aria-label="Close menu"
				></button>
			{/if}
			<Sidebar mobileOpen={mobileStore.drawerOpen} onMobileClose={mobileStore.close} />
		{/if}
		<main>
			{#key routeGroup}
				{@render children()}
			{/key}
		</main>
	</div>
</div>

<style>
	:global(:root) {
		--control-min-height: 36px;
		--control-padding-x: 12px;
		--control-chevron-width: 10px;
		--control-radius: 4px;
		--control-font-size: 0.85rem;
		--control-bg: #2a2a2a;
		--control-bg-hover: #3a3a3a;
		--control-border: #444;
		--control-text: #ccc;
		--control-text-hover: #fff;
		--control-focus: #6ea8fe;
		--control-primary-bg: #3a5a8a;
		--control-primary-bg-hover: #4a6a9a;
		--control-primary-text: #fff;
		--control-danger-bg: #5a2a2a;
		--control-danger-border: #844;
		--control-danger-bg-hover: #6a3a3a;
	}

	/* One box for every button, select and text field, so controls sitting
	   next to each other line up. Opt-in: icon-only chrome keeps its own. */
	:global(.control) {
		box-sizing: border-box;
		display: inline-flex;
		align-items: center;
		min-height: var(--control-min-height);
		padding: 0 var(--control-padding-x);
		border: 1px solid var(--control-border);
		border-radius: var(--control-radius);
		background: var(--control-bg);
		color: var(--control-text);
		font-size: var(--control-font-size);
		font-family: inherit;
		line-height: 1;
		cursor: pointer;
		white-space: nowrap;
	}

	:global(a.control) {
		text-decoration: none;
	}

	:global(a.control:hover),
	:global(button.control:hover:not(:disabled)) {
		background: var(--control-bg-hover);
		color: var(--control-text-hover);
		text-decoration: none;
	}

	:global(.control:focus-visible) {
		outline: none;
		border-color: var(--control-focus);
	}

	:global(.control:disabled) {
		opacity: 0.4;
		cursor: default;
	}

	:global(.control-primary) {
		background: var(--control-primary-bg);
		color: var(--control-primary-text);
	}

	:global(button.control-primary:hover:not(:disabled)) {
		background: var(--control-primary-bg-hover);
		color: var(--control-primary-text);
	}

	:global(.control-danger) {
		background: var(--control-danger-bg);
		border-color: var(--control-danger-border);
		color: var(--control-text);
	}

	:global(button.control-danger:hover:not(:disabled)) {
		background: var(--control-danger-bg-hover);
	}

	/* Text fields and selects wrap rather than nowrap, and fill their slot. */
	:global(input.control),
	:global(select.control),
	:global(textarea.control) {
		width: 100%;
		cursor: auto;
	}

	:global(select.control) {
		cursor: pointer;
		-webkit-appearance: none;
		appearance: none;
		/* height, not min-height: the box has to be imposed on a select,
		   which means it cannot grow with its content the way the others can. */
		height: var(--control-min-height);
		/* Room for the chevron: its own width plus a gap, past the usual
		   padding, so both track the padding token. The chevron's colour is
		   the one thing here that cannot: a custom property does not resolve
		   inside url(), so it repeats --control-text by hand. */
		padding-right: calc(var(--control-padding-x) + var(--control-chevron-width) + 8px);
		background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' fill='none' stroke='%23cccccc' stroke-width='1.5' stroke-linecap='round'/></svg>");
		background-repeat: no-repeat;
		background-position: right var(--control-padding-x) center;
		background-size: var(--control-chevron-width) 6px;
	}

	:global(input.control:focus),
	:global(select.control:focus) {
		outline: none;
		border-color: var(--control-focus);
	}

	/* A native date field sizes itself from the spinner, not from padding,
	   and comes out far taller than its neighbours without this. */
	:global(input[type='date'].control) {
		-webkit-appearance: none;
		appearance: none;
		/* As with a select, the height has to be imposed rather than a floor. */
		height: var(--control-min-height);
	}

	:global(input[type='date'].control::-webkit-date-and-time-value) {
		text-align: left;
		margin: 0;
	}

	:global(input[type='date'].control::-webkit-datetime-edit) {
		padding: 0;
	}

	:global(html) {
		-webkit-text-size-adjust: 100%;
		overflow: hidden;
		overscroll-behavior: none;
	}

	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: #111;
		color: #eee;
		overflow: hidden;
		overscroll-behavior: none;
	}

	/* Treat interactive chrome like app controls: no tap-highlight flash, no
	   double-tap zoom delay, and no accidental long-press text selection. */
	:global(button),
	:global(a),
	:global(.tap-target) {
		-webkit-tap-highlight-color: transparent;
		touch-action: manipulation;
	}

	:global(button),
	:global(.tap-target) {
		user-select: none;
		-webkit-user-select: none;
	}

	:global(a) {
		color: #6ea8fe;
		text-decoration: none;
	}

	:global(a:hover) {
		text-decoration: underline;
	}

	.app {
		display: flex;
		flex-direction: column;
		height: 100vh;
		height: 100dvh;
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.logo {
		font-size: 1.2rem;
		font-weight: 600;
		color: #eee;
	}

	.logo:hover {
		text-decoration: none;
	}

	nav {
		display: flex;
		gap: 16px;
	}

	.body {
		flex: 1;
		display: flex;
		overflow: hidden;
	}

	main {
		flex: 1;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	@media (max-width: 768px) {
		/* Safari zooms the page in when a field smaller than 16px takes focus,
		   and does not reliably zoom back out when the keyboard is dismissed.
		   Staying at 16px avoids the zoom rather than trying to undo it; the
		   whole scale moves together so controls still match each other. */
		:global(:root) {
			--control-font-size: 16px;
		}

		/* Pages render their own single-row mobile header, so the app header
		   is suppressed on mobile. */
		header {
			display: none;
		}

		.drawer-backdrop {
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, 0.55);
			z-index: 200;
			border: none;
			cursor: default;
		}

		/* Baseline touch targets. Controls that carry a screen's primary
		   action set their own, larger, minimum. */
		:global(button),
		:global(.tap-target) {
			min-height: 36px;
			min-width: 36px;
		}
	}
</style>
