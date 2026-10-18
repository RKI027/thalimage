<script lang="ts">
	import { formatSize } from '$lib/format';
	import type { EloStanding, ImageDetail, MetadataMode } from '$lib/types';
	import { getImageElo, getImageSidecars } from '$lib/api';
	import TagEditor from './TagEditor.svelte';
	import { distinctSidecars, type DistinctSidecar } from '$lib/sidecars';
	import { rankText, splitStandings } from '$lib/eloStanding';
	import ClippedText from './ClippedText.svelte';

	/** `collectionId` is the collection being browsed: its ELO standing comes first. */
	let {
		image,
		mode = 'full',
		collectionId
	}: { image: ImageDetail; mode?: MetadataMode; collectionId?: number } = $props();

	let standings = $state<EloStanding[]>([]);
	const elo = $derived(splitStandings(standings, collectionId));

	let sidecars = $state<DistinctSidecar[]>([]);


	$effect(() => {
		if (mode !== 'hidden' && image) {
			getImageElo(image.content_hash)
				.then((s) => (standings = s))
				.catch(() => (standings = []));
		}
	});

	$effect(() => {
		sidecars = [];
		if (mode === 'full' && image) {
			const hash = image.content_hash;
			getImageSidecars(hash)
				.then((s) => {
					if (image.content_hash === hash) sidecars = distinctSidecars(s);
				})
				.catch(() => {});
		}
	});


	function tryParseJSON(s: string | null): Record<string, unknown> | null {
		if (!s) return null;
		try {
			return JSON.parse(s);
		} catch {
			return null;
		}
	}
</script>

{#if mode !== 'hidden'}
<aside class="panel" class:compact={mode === 'compact'}>
	{#if mode === 'compact'}
		<div class="content">
			<dl>
				<dt>Name</dt><dd>{image.filename}</dd>
				<dt>Dimensions</dt><dd>{image.width} × {image.height}</dd>
				<dt>Format</dt><dd>{image.format}</dd>
				{#if elo.current}
					<dt>ELO</dt><dd>{Math.round(elo.current.score)} · {rankText(elo.current)}</dd>
				{/if}
			</dl>
		</div>
	{:else}
		<div class="content">
			<section>
				<h3>File</h3>
				<!-- One line per field, every field always there, so values sit in
				     the same place from one image to the next. -->
				<dl class="file">
					<dt>Name</dt><dd><ClippedText text={image.filename} /></dd>
					<dt>Original name</dt>
					<dd>
						<ClippedText
							text={image.original_name && image.original_name !== image.filename ? image.original_name : '—'}
						/>
					</dd>
					<dt>Size</dt><dd><ClippedText text={formatSize(image.file_size)} /></dd>
					<dt>Format</dt><dd><ClippedText text={image.format} /></dd>
					<dt>Dimensions</dt><dd><ClippedText text="{image.width} × {image.height}" /></dd>
					<dt>Aspect</dt><dd><ClippedText text={image.aspect_ratio.toFixed(2)} /></dd>
					<dt>Modified</dt><dd><ClippedText text={new Date(image.file_modified).toLocaleString()} /></dd>
					<dt>Created</dt>
					<dd><ClippedText text={image.file_created ? new Date(image.file_created).toLocaleString() : '—'} /></dd>
				</dl>
			</section>

			{#if standings.length > 0}
				<section>
					<h3>ELO</h3>
					{#if elo.current}
						<dl>
							<dt>Score</dt><dd>{Math.round(elo.current.score)}</dd>
							<dt>Rank</dt><dd>{rankText(elo.current)}</dd>
							<dt>Matches</dt>
							<dd>{elo.current.matches} ({elo.current.wins} won, {elo.current.losses} lost)</dd>
						</dl>
					{/if}
					{#if elo.others.length > 0}
						<h4>{elo.current ? 'In other collections' : 'By collection'}</h4>
						<dl>
							{#each elo.others as s (s.collection_id)}
								<dt>{s.collection_name}</dt><dd>{Math.round(s.score)} · {rankText(s)}</dd>
							{/each}
						</dl>
					{/if}
				</section>
			{/if}

			<section class="tags-section">
				<h3>Tags</h3>
				<TagEditor hash={image.content_hash} folderTags={image.folder_tags} />
			</section>

			{#if image.ai_tool || image.prompt || image.other_versions > 0}
				<section>
					<h3>AI Parameters</h3>
					{#if image.other_versions > 0}
						<p class="note">
							{image.other_versions === 1 ? 'Another file' : `${image.other_versions} other files`} of this
							image {image.other_versions === 1 ? 'has' : 'have'} a different prompt.
						</p>
					{/if}
					<dl>
						{#if image.ai_tool}
							<dt>Tool</dt><dd>{image.ai_tool}</dd>
						{/if}
						{#if image.prompt}
							<dt>Prompt</dt><dd class="wrap">{image.prompt}</dd>
						{/if}
						{#if image.negative_prompt}
							<dt>Negative</dt><dd class="wrap">{image.negative_prompt}</dd>
						{/if}
						{#if image.raw_params}
							<dt>Params</dt><dd class="wrap mono">{image.raw_params}</dd>
						{/if}
					</dl>
				</section>
			{/if}

			{#if image.png_text}
				{@const parsed = tryParseJSON(image.png_text)}
				{#if parsed}
					<section>
						<h3>PNG Text</h3>
						<dl>
							{#each Object.entries(parsed) as [key, val]}
								<dt>{key}</dt><dd class="wrap">{val}</dd>
							{/each}
						</dl>
					</section>
				{/if}
			{/if}

			{#if sidecars.length > 0}
				<details class="sidecars">
					<summary><h3>Sidecars ({sidecars.length})</h3></summary>
					{#each sidecars as sidecar (sidecar.names[0])}
						<h4 class="mono">{sidecar.names.join(', ')}</h4>
						{#if sidecar.text !== null}
							<pre class="wrap mono">{sidecar.text}</pre>
						{:else}
							<p class="note">{formatSize(sidecar.size)}, not shown</p>
						{/if}
					{/each}
				</details>
			{/if}
		</div>
	{/if}
</aside>
{/if}

<style>
	.panel {
		width: 320px;
		background: #1a1a1a;
		border-left: 1px solid #333;
		overflow-y: auto;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
	}

	.panel.compact {
		width: 200px;
	}

	.content {
		padding: 12px;
		overflow-y: auto;
	}

	section {
		margin-bottom: 16px;
	}

	h3 {
		margin: 0 0 8px;
		font-size: 0.85rem;
		color: #6ea8fe;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	dl {
		margin: 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 4px 12px;
		font-size: 0.85rem;
	}

	h4 {
		margin: 10px 0 6px;
		font-size: 0.75rem;
		font-weight: normal;
		color: #888;
	}

	dt {
		color: #888;
		white-space: nowrap;
	}

	dd {
		margin: 0;
		color: #ccc;
		word-break: break-word;
	}

	dl.file {
		grid-template-columns: auto minmax(0, 1fr);
	}

	dl.file dd {
		min-width: 0;
	}

	.wrap {
		white-space: pre-wrap;
		max-height: 200px;
		overflow-y: auto;
	}

	.mono {
		font-family: monospace;
		font-size: 0.8rem;
	}

	.sidecars {
		margin-bottom: 16px;
	}

	.sidecars summary {
		cursor: pointer;
	}

	.sidecars summary h3 {
		display: inline;
	}

	.sidecars h4 {
		word-break: break-all;
	}

	.sidecars pre {
		margin: 0;
		color: #ccc;
	}

	.note {
		margin: 0;
		font-size: 0.8rem;
		color: #888;
	}

	.tags-section {
		margin-top: 4px;
	}


	@media (max-width: 768px) {
		.panel,
		.panel.compact {
			width: 100%;
			border-left: none;
			border-top: 1px solid #333;
		}
	}
</style>
