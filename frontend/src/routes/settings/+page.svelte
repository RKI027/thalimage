<script lang="ts">
	import { page } from '$app/stores';
	import { listSources, createSource, deleteSource, triggerScan, subscribeScanProgress, getVersion } from '$lib/api';
	import { collectionsStore, sourcesStore, settingsStore } from '$lib/stores';
	import type { Source, VersionInfo } from '$lib/types';

	let sources: Source[] = $state([]);
	let newPath = $state('');
	let newLabel = $state('');
	let scanStatus: Record<number, string> = $state({});
	let backendVersion: string | null = $state(null);
	let backendCommit: string | null = $state(null);

	const buildCommit: string | null = __BUILD_COMMIT__;
	// Both halves ship from one commit; a mismatch means the frontend bundle
	// being served is older than the running backend.
	const stale = $derived(
		buildCommit !== null && backendCommit !== null && backendCommit !== buildCommit
	);

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
			collectionsStore.refresh();
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to add source');
		}
	}

	async function remove(id: number) {
		await deleteSource(id);
		await refresh();
		sourcesStore.refresh();
		collectionsStore.refresh();
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
					collectionsStore.refresh();
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
	onMount(() => {
		refresh();
		getVersion()
			.then((v: VersionInfo) => {
				backendVersion = v.version;
				backendCommit = v.commit;
			})
			.catch(() => {});
	});
</script>

<div class="settings-page">
	<div class="page-header">
		<h2>Settings</h2>
		<a href={backHref} class="close-btn">Close</a>
	</div>
	<section class="prefs-section">
		<h3>Preferences</h3>
		<div class="pref-row">
			<label for="nsfw-toggle">Show NSFW content</label>
			<input
				id="nsfw-toggle"
				type="checkbox"
				checked={$settingsStore.show_nsfw}
				onchange={() => settingsStore.patch({ show_nsfw: !$settingsStore.show_nsfw })}
			/>
		</div>
	</section>

	<h3>Source Folders</h3>
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
						<button class="danger" onclick={() => remove(source.id)}>Remove</button>
					</div>
				</li>
			{/each}
		</ul>
	{/if}

	<section class="about">
		<h3>About</h3>
		<dl>
			<dt>Backend</dt>
			<dd>{backendVersion ? `${backendVersion} (${backendCommit ?? 'unknown commit'})` : '…'}</dd>
			<dt>Frontend</dt>
			<dd>{buildCommit ?? 'unknown commit'}</dd>
		</dl>
		{#if stale}
			<p class="stale">This page was built from a different commit than the
				running backend. Rebuild the frontend to match.</p>
		{/if}
	</section>
</div>

<style>
	.settings-page {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior-y: contain;
		padding: calc(24px + env(safe-area-inset-top)) max(24px, env(safe-area-inset-right))
			calc(24px + env(safe-area-inset-bottom)) max(24px, env(safe-area-inset-left));
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

	.prefs-section {
		margin-bottom: 32px;
	}

	.prefs-section h3 {
		margin: 0 0 12px;
		font-size: 1rem;
		color: #ccc;
	}

	.pref-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 0;
		border-bottom: 1px solid #2a2a2a;
		font-size: 0.9rem;
		color: #ccc;
	}

	.pref-row label {
		flex: 1;
		cursor: pointer;
	}

	.pref-row input[type='checkbox'] {
		width: 16px;
		height: 16px;
		cursor: pointer;
		padding: 0;
		border: none;
		background: none;
		flex: none;
	}

	.add-form {
		display: flex;
		flex-wrap: wrap;
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

	/* Inputs default to min-width:auto, which is the placeholder's width and
	   wide enough to push the row off a phone screen. */
	.path-input {
		flex: 2;
		min-width: 0;
	}

	.label-input {
		flex: 1;
		min-width: 0;
	}

	button {
		padding: 6px 16px;
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
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		padding: 16px 8px;
		border-bottom: 1px solid #2a2a2a;
	}

	.source-info {
		display: flex;
		flex-direction: column;
		gap: 4px;
		flex: 1;
		min-width: 0;
		/* An unlabelled source shows its path as the title; paths have no
		   spaces to break at and would otherwise run under the buttons. */
		overflow-wrap: anywhere;
	}

	.path {
		color: #888;
		font-size: 0.85rem;
		font-family: monospace;
		/* Folder paths have no spaces to break at. */
		overflow-wrap: anywhere;
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

	.about {
		margin-top: 40px;
		padding-top: 16px;
		border-top: 1px solid #2a2a2a;
	}

	.about h3 {
		margin: 0 0 12px;
		font-size: 1rem;
		color: #ccc;
	}

	.about dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 4px 16px;
		margin: 0;
		font-size: 0.85rem;
	}

	.about dt {
		color: #888;
	}

	.about dd {
		margin: 0;
		color: #ccc;
		font-family: monospace;
		overflow-wrap: anywhere;
	}

	.stale {
		margin: 12px 0 0;
		color: #e0a458;
		font-size: 0.85rem;
	}

	@media (max-width: 768px) {
		/* Two inputs and a button do not fit a phone row. */
		.add-form {
			flex-direction: column;
			align-items: stretch;
		}

		/* Side by side, a path and its buttons leave both cramped. */
		li {
			flex-direction: column;
			align-items: stretch;
		}
	}
</style>
