<script lang="ts">
	import { summaryHeadline, summaryLines } from '$lib/sourceSummary';
	import type { SourceSummary } from '$lib/types';

	/** A source's files set against its images, each difference opening onto its files. */
	let { summary }: { summary: SourceSummary } = $props();

	const lines = $derived(summaryLines(summary));
</script>

<div class="breakdown">
	<span class="headline">{summaryHeadline(summary)}</span>
	{#each lines as line (line.kind)}
		<details>
			<summary>{line.label}</summary>
			<ul>
				{#if line.kind === 'duplicates'}
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
</div>

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

	.reason {
		color: #a77;
	}
</style>
