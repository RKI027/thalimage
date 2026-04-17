<script lang="ts">
	import { onMount } from 'svelte';
	import { listCollections, createCollection, deleteCollection } from '$lib/api';
	import { collectionsStore } from '$lib/stores';
	import type { Collection } from '$lib/types';

	let presets: Collection[] = $state([]);
	let collections: Collection[] = $state([]);
	let newName = $state('');

	async function refresh() {
		const all = await listCollections();
		presets = all.filter((c) => c.type === 'source_preset');
		collections = all.filter((c) => c.type === 'manual');
	}

	async function addCollection() {
		if (!newName.trim()) return;
		await createCollection(newName.trim());
		newName = '';
		await refresh();
		collectionsStore.refresh();
	}

	async function remove(id: number) {
		await deleteCollection(id);
		await refresh();
		collectionsStore.refresh();
	}

	onMount(() => { refresh(); });
</script>

<div class="collections-page">
	{#if presets.length > 0}
		<section>
			<h3 class="section-label">Presets</h3>
			<ul>
				<li>
					<a href="/">
						<span class="name">All Images</span>
					</a>
				</li>
				{#each presets as preset}
					<li>
						<a href="/collections/{preset.id}">
							<span class="name">{preset.name}</span>
							<span class="count">{preset.image_count} images</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<section>
		<h3 class="section-label">Collections</h3>

		<div class="add-form">
			<input bind:value={newName} placeholder="New collection name" onkeydown={(e) => e.key === 'Enter' && addCollection()} />
			<button onclick={addCollection}>Create</button>
		</div>

		{#if collections.length === 0}
			<p class="empty">No collections yet. Create one above.</p>
		{:else}
			<ul>
				{#each collections as coll}
					<li>
						<a href="/collections/{coll.id}">
							<span class="name">{coll.name}</span>
							<span class="count">{coll.image_count} images</span>
						</a>
						<button class="delete" onclick={() => remove(coll.id)}>×</button>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
</div>

<style>
	.collections-page {
		padding: 24px;
		max-width: 600px;
	}

	section {
		margin-bottom: 32px;
	}

	.section-label {
		margin: 0 0 12px;
		font-size: 0.8rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.add-form {
		display: flex;
		gap: 8px;
		margin-bottom: 16px;
	}

	input {
		flex: 1;
		padding: 8px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #eee;
		font-size: 0.9rem;
	}

	button {
		padding: 8px 16px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #3a5a8a;
		color: #fff;
		cursor: pointer;
	}

	button:hover {
		background: #4a6a9a;
	}

	.empty {
		color: #666;
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	li {
		display: flex;
		align-items: center;
		border-bottom: 1px solid #2a2a2a;
	}

	li a {
		flex: 1;
		display: flex;
		justify-content: space-between;
		padding: 12px 8px;
		color: #ccc;
	}

	li a:hover {
		background: #1a1a1a;
		text-decoration: none;
	}

	.count {
		color: #888;
		font-size: 0.85rem;
	}

	.delete {
		background: transparent;
		border: none;
		color: #666;
		font-size: 1.2rem;
		padding: 8px;
		cursor: pointer;
	}

	.delete:hover {
		color: #f66;
		background: transparent;
	}
</style>
