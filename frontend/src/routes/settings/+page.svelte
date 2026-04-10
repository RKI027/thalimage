<script lang="ts">
	import { page } from '$app/stores';
	import { listSources, createSource, deleteSource, triggerScan, subscribeScanProgress, createCollectionFromSource } from '$lib/api';
	import { collectionsStore, sourcesStore } from '$lib/stores';
	import type { Source } from '$lib/types';

	let sources: Source[] = $state([]);
	let newPath = $state('');
	let newLabel = $state('');
	let scanStatus: Record<number, string> = $state({});

	const backHref = $derived($page.url.searchParams.get('returnTo') || '/');

	async function refresh() {
		sources = await listSources();
	}

	async function addSource() {
		if (!newPath.trim()) return;
		try {
			await createSource(newPath.trim(), newLabel.trim() || undefined);
			newPath = '';
			newLabel = '';
			await refresh();
			sourcesStore.refresh();
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to add source');
		}
	}

	async function remove(id: number) {
		await deleteSource(id);
		await refresh();
		sourcesStore.refresh();
	}

	async function makeCollection(id: number) {
		try {
			const result = await createCollectionFromSource(id);
			scanStatus[id] = `Collection "${result.name}" created with ${result.image_count} images`;
			collectionsStore.refresh();
		} catch (e) {
			scanStatus[id] = e instanceof Error ? e.message : 'Failed to create collection';
		}
	}

	async function scan(id: number) {
		scanStatus[id] = 'Starting…';
		try {
			await triggerScan(id);
			const unsubscribe = subscribeScanProgress(id, (p) => {
				if (p.phase === 'processing') {
					scanStatus[id] = `Processing ${p.current}/${p.total}…`;
				} else if (p.phase === 'complete') {
					scanStatus[id] = `Done: ${p.added} added, ${p.skipped} skipped, ${p.errors} errors`;
					unsubscribe();
					refresh();
					sourcesStore.refresh();
				} else if (p.phase === 'error') {
					scanStatus[id] = `Error: ${p.message || 'Scan failed'}`;
					unsubscribe();
				}
			});
		} catch {
			scanStatus[id] = 'Scan failed';
		}
	}

	import { onMount } from 'svelte';
	onMount(() => { refresh(); });
</script>

<div class="settings-page">
	<div class="page-header">
		<h2>Source Folders</h2>
		<a href={backHref} class="close-btn">Close</a>
	</div>
	<p class="description">Add folders containing your AI-generated images. Thalimage will scan them for images and extract metadata.</p>

	<div class="add-form">
		<input bind:value={newPath} placeholder="Folder path (e.g. /photos/ai)" class="path-input" />
		<input bind:value={newLabel} placeholder="Label (optional)" class="label-input" />
		<button onclick={addSource}>Add</button>
	</div>

	{#if sources.length === 0}
		<p class="empty">No source folders configured.</p>
	{:else}
		<ul>
			{#each sources as source}
				<li>
					<div class="source-info">
						<strong>{source.label || source.path}</strong>
						{#if source.label}
							<span class="path">{source.path}</span>
						{/if}
						{#if source.last_scan}
							<span class="meta">Last scan: {new Date(source.last_scan).toLocaleString()}</span>
						{:else}
							<span class="meta">Not yet scanned</span>
						{/if}
						{#if scanStatus[source.id]}
							<span class="scan-status">{scanStatus[source.id]}</span>
						{/if}
					</div>
					<div class="source-actions">
						<button onclick={() => scan(source.id)}>Scan</button>
						<button onclick={() => makeCollection(source.id)}>Create Collection</button>
						<button class="danger" onclick={() => remove(source.id)}>Remove</button>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.settings-page {
		padding: 24px;
		max-width: 700px;
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}

	h2 {
		margin: 0;
	}

	.close-btn {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		font-size: 0.85rem;
	}

	.close-btn:hover {
		background: #3a3a3a;
		text-decoration: none;
	}

	.description {
		color: #888;
		margin: 0 0 24px;
		font-size: 0.9rem;
	}

	.add-form {
		display: flex;
		gap: 8px;
		margin-bottom: 24px;
	}

	input {
		padding: 8px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #eee;
		font-size: 0.9rem;
	}

	.path-input {
		flex: 2;
	}

	.label-input {
		flex: 1;
	}

	button {
		padding: 8px 16px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #3a5a8a;
		color: #fff;
		cursor: pointer;
		white-space: nowrap;
	}

	button:hover {
		background: #4a6a9a;
	}

	button.danger {
		background: #5a2a2a;
		border-color: #844;
	}

	button.danger:hover {
		background: #6a3a3a;
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
		justify-content: space-between;
		align-items: flex-start;
		padding: 16px 8px;
		border-bottom: 1px solid #2a2a2a;
	}

	.source-info {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.path {
		color: #888;
		font-size: 0.85rem;
		font-family: monospace;
	}

	.meta {
		color: #666;
		font-size: 0.8rem;
	}

	.scan-status {
		color: #6ea8fe;
		font-size: 0.8rem;
	}

	.source-actions {
		display: flex;
		gap: 8px;
		flex-shrink: 0;
	}
</style>
