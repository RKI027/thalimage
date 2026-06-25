<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import { slideshowStore } from '$lib/slideshowStore.svelte';
	import { mobileStore } from '$lib/mobileStore.svelte';
	import { settingsStore } from '$lib/stores';

	let { children } = $props();

	onMount(() => { settingsStore.refresh(); });

	const isSlideshow = $derived(slideshowStore.status !== 'idle');
	const routeGroup = $derived($page.url.pathname.split('/')[1] || 'home');

	const settingsHref = $derived(
		$page.url.pathname === '/settings'
			? '/settings'
			: `/settings?returnTo=${encodeURIComponent($page.url.pathname + $page.url.search)}`
	);
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
				<a href={settingsHref}>Settings</a>
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
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: #111;
		color: #eee;
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

		/* Global touch targets */
		:global(button),
		:global(.tap-target) {
			min-height: 44px;
			min-width: 44px;
		}
	}
</style>
