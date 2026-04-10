<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { collectionsStore } from '$lib/stores';

	let open = $state(true);
	let presetsOpen = $state(true);
	let collectionsOpen = $state(true);

	const presets = $derived($collectionsStore.filter((c) => c.type === 'source_preset'));
	const userCollections = $derived($collectionsStore.filter((c) => c.type === 'manual'));

	const settingsHref = $derived(
		$page.url.pathname === '/settings'
			? '/settings'
			: `/settings?returnTo=${encodeURIComponent($page.url.pathname + $page.url.search)}`
	);

	onMount(() => {
		collectionsStore.refresh();
		presetsOpen = localStorage.getItem('sidebar:presets') !== 'false';
		collectionsOpen = localStorage.getItem('sidebar:collections') !== 'false';
	});

	function togglePresets() {
		presetsOpen = !presetsOpen;
		localStorage.setItem('sidebar:presets', String(presetsOpen));
	}

	function toggleCollections() {
		collectionsOpen = !collectionsOpen;
		localStorage.setItem('sidebar:collections', String(collectionsOpen));
	}
</script>

<aside class="sidebar" class:collapsed={!open}>
	<button class="toggle" onclick={() => (open = !open)}>
		{open ? '◀' : '▶'}
	</button>

	{#if open}
		<nav>
			<section>
				<button class="section-header" onclick={togglePresets}>
					<span>{presetsOpen ? '▼' : '▶'}</span>
					<h3>Presets</h3>
				</button>
				{#if presetsOpen}
					<ul>
						<li><a href="/">All Images</a></li>
						{#each presets as preset}
							<li>
								<a href="/collections/{preset.id}">
									{preset.name}
									<span class="badge">{preset.image_count}</span>
								</a>
							</li>
						{/each}
					</ul>
				{/if}
			</section>

			<section>
				<div class="section-header-row">
					<button class="section-header" onclick={toggleCollections}>
						<span>{collectionsOpen ? '▼' : '▶'}</span>
						<h3>Collections</h3>
					</button>
					<a href="/collections" class="manage-link" title="Manage collections">⚙</a>
				</div>
				{#if collectionsOpen}
					{#if userCollections.length === 0}
						<p class="empty">No collections yet</p>
					{:else}
						<ul>
							{#each userCollections as coll}
								<li>
									<a href="/collections/{coll.id}">
										{coll.name}
										<span class="badge">{coll.image_count}</span>
									</a>
								</li>
							{/each}
						</ul>
					{/if}
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

	.section-header-row {
		display: flex;
		align-items: center;
		margin-bottom: 8px;
	}

	.section-header-row .section-header {
		margin-bottom: 0;
	}

	.manage-link {
		margin-left: auto;
		color: #666;
		font-size: 0.85rem;
		text-decoration: none;
		padding: 0 4px;
	}

	.manage-link:hover {
		color: #ccc;
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: 4px;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		width: 100%;
		margin-bottom: 8px;
	}

	.section-header span {
		color: #666;
		font-size: 0.7rem;
		width: 12px;
	}

	.section-header h3 {
		margin: 0;
		font-size: 0.8rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.section-header:hover h3 {
		color: #aaa;
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
