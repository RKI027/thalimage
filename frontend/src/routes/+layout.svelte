<script lang="ts">
	import Sidebar from '$lib/components/Sidebar.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<title>Thalimage</title>
</svelte:head>

<div class="app">
	<header>
		<a href="/" class="logo">Thalimage</a>
		<nav>
			<a href="/">Gallery</a>
			<a href="/settings">Settings</a>
		</nav>
	</header>
	<div class="body">
		<Sidebar />
		<main>
			{@render children()}
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
</style>
