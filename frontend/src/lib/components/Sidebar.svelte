<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { listSources, listCollections } from '$lib/api';
	import type { Source, Collection } from '$lib/types';

	let sources: Source[] = $state([]);
	let collections: Collection[] = $state([]);
	let open = $state(true);

	async function refresh() {
		[sources, collections] = await Promise.all([listSources(), listCollections()]);
	}

	// Re-fetch on route change so changes from Settings/Collections are picked up
	$effect(() => {
		void $page.url.pathname;
		untrack(() => { refresh(); });
	});
</script>

<aside class="sidebar" class:collapsed={!open}>
	<button class="toggle" onclick={() => (open = !open)}>
		{open ? '◀' : '▶'}
	</button>

	{#if open}
		<nav>
			<section>
				<h3>Sources</h3>
				{#if sources.length === 0}
					<p class="empty">No sources. <a href="/settings">Add one</a></p>
				{:else}
					<ul>
						<li><a href="/">All</a></li>
						{#each sources as source}
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
				{#if collections.length === 0}
					<p class="empty">No collections yet</p>
				{:else}
					<ul>
						{#each collections as coll}
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
				<a href="/settings" class="settings-link">Settings</a>
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
