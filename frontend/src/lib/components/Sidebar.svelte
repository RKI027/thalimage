<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { sourcesStore, collectionsStore } from '$lib/stores';

	let open = $state(true);

	onMount(() => {
		sourcesStore.refresh();
		collectionsStore.refresh();
	});

	const settingsHref = $derived(
		$page.url.pathname === '/settings'
			? '/settings'
			: `/settings?returnTo=${encodeURIComponent($page.url.pathname + $page.url.search)}`
	);
</script>

<aside class="sidebar" class:collapsed={!open}>
	<button class="toggle" onclick={() => (open = !open)}>
		{open ? '◀' : '▶'}
	</button>

	{#if open}
		<nav>
			<section>
				<h3>Sources</h3>
				{#if $sourcesStore.length === 0}
					<p class="empty">No sources. <a href={settingsHref}>Add one</a></p>
				{:else}
					<ul>
						<li><a href="/">All</a></li>
						{#each $sourcesStore as source}
							<li>
								<a href="/?source_id={source.id}">
									{source.label || source.path}
								</a>
								{#if source.last_scan}
									<span class="meta">Last scan: {new Date(source.last_scan).toLocaleDateString()}</span>
								{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</section>

			<section>
				<h3>Collections</h3>
				{#if $collectionsStore.length === 0}
					<p class="empty">No collections yet</p>
				{:else}
					<ul>
						{#each $collectionsStore as coll}
							<li>
								<a href="/collections/{coll.id}">
									{coll.name}
									<span class="badge">{coll.image_count}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</section>

			<section>
				<a href={settingsHref} class="settings-link">Settings</a>
			</section>
		</nav>
	{/if}
</aside>

<style>
	.sidebar {
		width: 240px;
		background: #1a1a1a;
		border-right: 1px solid #333;
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		overflow-y: auto;
	}

	.sidebar.collapsed {
		width: auto;
	}

	.toggle {
		background: #2a2a2a;
		border: none;
		color: #ccc;
		padding: 8px;
		cursor: pointer;
		text-align: center;
		border-bottom: 1px solid #333;
	}

	.toggle:hover {
		background: #3a3a3a;
	}

	nav {
		padding: 12px;
	}

	section {
		margin-bottom: 16px;
	}

	h3 {
		margin: 0 0 8px;
		font-size: 0.8rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		margin-bottom: 4px;
	}

	li a {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 4px 8px;
		border-radius: 4px;
		color: #ccc;
		font-size: 0.9rem;
	}

	li a:hover {
		background: #2a2a2a;
		text-decoration: none;
	}

	.badge {
		background: #333;
		padding: 1px 6px;
		border-radius: 10px;
		font-size: 0.75rem;
		color: #888;
	}

	.meta {
		display: block;
		font-size: 0.75rem;
		color: #666;
		padding-left: 8px;
	}

	.empty {
		color: #666;
		font-size: 0.85rem;
		padding: 0 8px;
	}

	.settings-link {
		display: block;
		padding: 8px;
		color: #888;
		font-size: 0.85rem;
	}
</style>
