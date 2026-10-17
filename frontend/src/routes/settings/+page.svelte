<script lang="ts">
	import { page } from '$app/stores';
	import { listSources, createSource, deleteSource, triggerScan, subscribeScanProgress, getVersion, getSourceSummary, updateSource } from '$lib/api';
	import { collectionsStore, settingsStore } from '$lib/stores';
	import { scanDoneMessage } from '$lib/scanStatus';
	import BackupSettings from '$lib/components/BackupSettings.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import SourceBreakdown from '$lib/components/SourceBreakdown.svelte';
	import type { Source, SourceSummary, VersionInfo } from '$lib/types';

	let sources: Source[] = $state([]);
	let newPath = $state('');
	let newLabel = $state('');
	let newWritable = $state(false);
	let relabelling: number | null = $state(null);
	let removing: Source | null = $state(null);
	let keepData = $state(true);
	let scanStatus: Record<number, string> = $state({});
	let summaries: Record<number, SourceSummary> = $state({});
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
		const loaded = await Promise.all(sources.map((s) => getSourceSummary(s.id)));
		summaries = Object.fromEntries(sources.map((s, i) => [s.id, loaded[i]]));
	}

	async function addSource() {
		if (!newPath.trim()) return;
		try {
			await createSource(newPath.trim(), newLabel.trim() || undefined, { writable: newWritable });
			newPath = '';
			newLabel = '';
			newWritable = false;
			await refresh();
			collectionsStore.refresh();
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to add source');
		}
	}

	async function setFlag(source: Source, flag: 'writable' | 'rename_to_hash', box: HTMLInputElement) {
		try {
			await updateSource(source.id, { [flag]: box.checked });
		} catch (e) {
			// The box was ticked by hand; the source did not change, so put it back.
			box.checked = source[flag];
			alert(e instanceof Error ? e.message : 'Failed to change the source');
		}
		await refresh();
	}

	async function relabel(source: Source, label: string) {
		// Enter saves and then blurs the field; only the first save counts.
		if (relabelling !== source.id) return;
		relabelling = null;
		if (label.trim() === (source.label ?? '')) return;
		try {
			await updateSource(source.id, { label });
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to relabel the source');
		}
		await refresh();
		collectionsStore.refresh();
	}

	function relabelKey(source: Source, e: KeyboardEvent & { currentTarget: HTMLInputElement }) {
		if (e.key === 'Enter') relabel(source, e.currentTarget.value);
		else if (e.key === 'Escape') relabelling = null;
	}

	function askRemove(source: Source) {
		keepData = true;
		removing = source;
	}

	async function remove() {
		if (!removing) return;
		const id = removing.id;
		removing = null;
		try {
			await deleteSource(id, { keepData });
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to remove the source');
		}
		await refresh();
		collectionsStore.refresh();
	}

	async function scan(id: number) {
		scanStatus[id] = 'Starting…';
		try {
			await triggerScan(id);
			const unsubscribe = subscribeScanProgress(id, (p) => {
				if (p.phase === 'processing') {
					scanStatus[id] = `Processing ${p.current}/${p.total}…`;
				} else if (p.phase === 'checking') {
					scanStatus[id] = `Checking videos ${p.current}/${p.total}…`;
				} else if (p.phase === 'converting') {
					scanStatus[id] = `Making videos playable on iOS ${p.current}/${p.total}…`;
				} else if (p.phase === 'complete') {
					scanStatus[id] = scanDoneMessage(p);
					unsubscribe();
					refresh();
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
		<a href={backHref} class="control">Close</a>
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

	<BackupSettings />

	<h3>Source Folders</h3>
	<p class="description">Add folders containing your AI-generated images. Thalimage will scan them for images and extract metadata.</p>

	<div class="add-form">
		<input bind:value={newPath} placeholder="Folder path (e.g. /photos/ai)" class="control path-input" />
		<input bind:value={newLabel} placeholder="Label (optional)" class="control label-input" />
		<button class="control control-primary" onclick={addSource}>Add</button>
	</div>
	<label class="writable">
		<input type="checkbox" bind:checked={newWritable} />
		Thalimage may change files in this folder (delete, rename, move)
	</label>

	{#if sources.length === 0}
		<p class="empty">No source folders configured.</p>
	{:else}
		<ul>
			{#each sources as source}
				<li>
					<div class="source-info">
						{#if relabelling === source.id}
							<!-- svelte-ignore a11y_autofocus -->
							<input
								class="control"
								value={source.label ?? ''}
								placeholder="Label (blank for none)"
								aria-label="Label"
								autofocus
								onkeydown={(e) => relabelKey(source, e)}
								onblur={(e) => relabel(source, e.currentTarget.value)}
							/>
						{:else}
							<strong>{source.label || source.path}</strong>
						{/if}
						{#if source.label}
							<span class="path">{source.path}</span>
						{/if}
						{#if source.last_scan}
							<span class="meta">Last scan: {new Date(source.last_scan).toLocaleString()}</span>
						{:else}
							<span class="meta">Not yet scanned</span>
						{/if}
						<label class="writable">
							<input
								type="checkbox"
								checked={source.writable}
								onchange={(e) => setFlag(source, 'writable', e.currentTarget)}
							/>
							{source.writable ? 'Thalimage may change files here' : 'Read-only: Thalimage never changes files here'}
						</label>
						{#if source.writable}
							<label class="writable">
								<input
									type="checkbox"
									checked={source.rename_to_hash}
									onchange={(e) => setFlag(source, 'rename_to_hash', e.currentTarget)}
								/>
								Rename files to their picture hash at each scan
							</label>
						{/if}
						{#if summaries[source.id] && source.last_scan}
							<SourceBreakdown
								summary={summaries[source.id]}
								sourceId={source.id}
								writable={source.writable}
								onchange={refresh}
							/>
						{/if}
						{#if scanStatus[source.id]}
							<span class="scan-status">{scanStatus[source.id]}</span>
						{/if}
					</div>
					<div class="source-actions">
						<button class="control control-primary" onclick={() => scan(source.id)}>Scan</button>
						<button class="control" onclick={() => (relabelling = source.id)}>Relabel</button>
						<button class="control control-danger" onclick={() => askRemove(source)}>Remove…</button>
					</div>
				</li>
			{/each}
		</ul>
	{/if}

	{#if removing}
		{@const onlyHere = summaries[removing.id]?.only_here ?? 0}
		<ConfirmDialog
			open
			title="Remove {removing.label || removing.path}?"
			confirmLabel={keepData ? 'Remove source' : 'Remove source and data'}
			danger={!keepData && onlyHere > 0}
			onconfirm={remove}
			oncancel={() => (removing = null)}
		>
			<p>
				The files on disk are not touched, and the source's preset collection goes.
				{#if onlyHere === 0}
					Every image in it also lies in another source and keeps its data.
				{:else}
					{onlyHere.toLocaleString('en-US')} {onlyHere === 1 ? 'image is' : 'images are'} found
					in no other source:
				{/if}
			</p>
			{#if onlyHere > 0}
				<label class="choice">
					<input type="radio" name="keep-data" value={true} bind:group={keepData} />
					<span><strong>Keep their data</strong>: tags, scores and collection memberships stay,
						hidden, and come back when a scan finds the same pictures again.</span>
				</label>
				<label class="choice">
					<input type="radio" name="keep-data" value={false} bind:group={keepData} />
					<span><strong>Remove their data</strong>: delete them from the database with their
						tags, scores and collection memberships. This cannot be undone.</span>
				</label>
			{/if}
		</ConfirmDialog>
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

	.choice {
		display: flex;
		align-items: baseline;
		gap: 8px;
		margin: 8px 0;
	}

	.writable {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.8rem;
		color: #888;
	}

	.add-form + .writable {
		margin: -8px 0 16px;
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
