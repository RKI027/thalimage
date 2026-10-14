<script lang="ts">
	import { deleteCopies } from '$lib/api';
	import { allButFirst, canSelect, toggled } from '$lib/copySelection';
	import { summaryHeadline, summaryLines } from '$lib/sourceSummary';
	import type { SourceSummary } from '$lib/types';
	import ConfirmDialog from './ConfirmDialog.svelte';

	/**
	 * A source's files set against its images, each difference opening onto
	 * its files. In a writable source, duplicate copies can be deleted;
	 * `onchange` runs after a deletion so the summary can reload.
	 */
	let {
		summary,
		sourceId,
		writable,
		onchange
	}: { summary: SourceSummary; sourceId: number; writable: boolean; onchange: () => void } =
		$props();

	const lines = $derived(summaryLines(summary));
	let selected = $state(new Set<string>());
	let confirming = $state(false);
	let message = $state('');

	async function deleteSelected() {
		confirming = false;
		const paths = [...selected];
		try {
			const result = await deleteCopies(sourceId, paths);
			message = result.failed.length
				? `Deleted ${result.deleted.length}; failed: ` +
					result.failed.map((f) => `${f.relative_path} (${f.error})`).join(', ')
				: `Deleted ${result.deleted.length} ${result.deleted.length === 1 ? 'copy' : 'copies'}.`;
		} catch (e) {
			message = e instanceof Error ? e.message : 'Delete failed';
		}
		selected = new Set();
		onchange();
	}
</script>

<div class="breakdown">
	<span class="headline">{summaryHeadline(summary)}</span>
	{#each lines as line (line.kind)}
		<details>
			<summary>{line.label}</summary>
			<ul>
				{#if line.kind === 'duplicates' && writable}
					<li class="tools">
						<button class="link" onclick={() => (selected = allButFirst(summary.duplicates))}>
							Select all but one of each
						</button>
						<button
							class="control control-danger"
							disabled={selected.size === 0}
							onclick={() => (confirming = true)}
						>
							Delete {selected.size} selected
						</button>
					</li>
					{#each summary.duplicates as group (group.content_hash)}
						<li>
							<a href="/image/{group.content_hash}">view</a>
							{#each group.paths as path (path)}
								<label class="copy">
									<input
										type="checkbox"
										checked={selected.has(path)}
										disabled={!canSelect(group, selected, path)}
										onchange={() => (selected = toggled(selected, path))}
									/>
									{path}
								</label>
							{/each}
						</li>
					{/each}
				{:else if line.kind === 'duplicates'}
					<li class="hint">Mark this source writable to delete copies.</li>
					{#each summary.duplicates as group (group.content_hash)}
						<li>
							<a href="/image/{group.content_hash}">{group.paths[0]}</a>
							{#each group.paths.slice(1) as path}
								<span class="copy">= {path}</span>
							{/each}
						</li>
					{/each}
				{:else if line.kind === 'failures'}
					{#each summary.failures as failure (failure.relative_path)}
						<li>{failure.relative_path} <span class="reason">— {failure.reason}</span></li>
					{/each}
				{:else}
					{#each summary.archived as file (file.content_hash)}
						<li><a href="/image/{file.content_hash}">{file.relative_path}</a></li>
					{/each}
				{/if}
			</ul>
		</details>
	{/each}
	{#if message}
		<span class="message">{message}</span>
	{/if}
</div>

<ConfirmDialog
	open={confirming}
	title="Delete {selected.size} {selected.size === 1 ? 'file' : 'files'} from disk?"
	confirmLabel="Delete permanently"
	danger
	onconfirm={deleteSelected}
	oncancel={() => (confirming = false)}
>
	<p>
		These files will be removed from the disk. This cannot be undone. Each is a copy of an image
		that keeps at least one other copy.
	</p>
	<ul class="confirm-list">
		{#each [...selected] as path (path)}
			<li>{path}</li>
		{/each}
	</ul>
</ConfirmDialog>

<style>
	.breakdown {
		display: flex;
		flex-direction: column;
		gap: 2px;
		font-size: 0.8rem;
		color: #888;
	}

	summary {
		cursor: pointer;
	}

	ul {
		list-style: none;
		margin: 4px 0 6px;
		padding-left: 14px;
		max-height: 240px;
		overflow-y: auto;
		overflow-wrap: anywhere;
	}

	li {
		padding: 1px 0;
	}

	.copy {
		display: block;
		padding-left: 12px;
	}

	.copy input {
		margin: 0 4px 0 0;
		vertical-align: middle;
	}

	.tools {
		display: flex;
		align-items: center;
		gap: 12px;
		padding-bottom: 6px;
	}

	.link {
		background: none;
		border: none;
		padding: 0;
		color: #6ea8fe;
		cursor: pointer;
		font: inherit;
	}

	.hint,
	.message {
		font-style: italic;
	}

	.confirm-list {
		list-style: disc;
		padding-left: 20px;
		max-height: none;
	}

	.reason {
		color: #a77;
	}
</style>
