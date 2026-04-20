<script lang="ts">
	import type { ImageDetail, MetadataMode, Tag } from '$lib/types';
	import { getImageTags, addImageTag, removeImageTag, listTags, createTag } from '$lib/api';

	let { image, mode = 'full' }: { image: ImageDetail; mode?: MetadataMode } = $props();

	let tags = $state<Tag[]>([]);
	let tagInput = $state('');
	let tagSuggestions = $state<Tag[]>([]);
	let tagInputDebounce: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		if (mode !== 'hidden' && image) {
			getImageTags(image.content_hash).then((t) => (tags = t));
		}
	});

	async function onTagInput(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		tagInput = val;
		if (tagInputDebounce) clearTimeout(tagInputDebounce);
		if (!val.trim()) { tagSuggestions = []; return; }
		tagInputDebounce = setTimeout(async () => {
			tagSuggestions = await listTags(val.trim());
		}, 200);
	}

	async function selectTag(tag: Tag) {
		await addImageTag(image.content_hash, tag.id);
		tags = await getImageTags(image.content_hash);
		tagInput = '';
		tagSuggestions = [];
	}

	async function addNewTag(name: string) {
		const tag = await createTag(name.trim());
		await addImageTag(image.content_hash, tag.id);
		tags = await getImageTags(image.content_hash);
		tagInput = '';
		tagSuggestions = [];
	}

	async function onTagInputKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && tagInput.trim()) {
			e.preventDefault();
			const name = tagInput.trim();
			const existing = tagSuggestions.find((t) => t.name.toLowerCase() === name.toLowerCase());
			if (existing) {
				await selectTag(existing);
			} else {
				await addNewTag(name);
			}
		} else if (e.key === 'Escape') {
			tagInput = '';
			tagSuggestions = [];
		}
	}

	async function removeTag(tag: Tag) {
		await removeImageTag(image.content_hash, tag.id);
		tags = tags.filter((t) => t.id !== tag.id);
	}

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

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
			</dl>
		</div>
	{:else}
		<div class="content">
			<section>
				<h3>File</h3>
				<dl>
					<dt>Name</dt><dd>{image.filename}</dd>
					<dt>Size</dt><dd>{formatSize(image.file_size)}</dd>
					<dt>Format</dt><dd>{image.format}</dd>
					<dt>Dimensions</dt><dd>{image.width} × {image.height}</dd>
					<dt>Aspect</dt><dd>{image.aspect_ratio.toFixed(2)}</dd>
					<dt>Modified</dt><dd>{new Date(image.file_modified).toLocaleString()}</dd>
					{#if image.file_created}
						<dt>Created</dt><dd>{new Date(image.file_created).toLocaleString()}</dd>
					{/if}
				</dl>
			</section>

			{#if image.ai_tool || image.prompt}
				<section>
					<h3>AI Parameters</h3>
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

			<section class="tags-section">
				<h3>Tags</h3>
				<div class="tag-list">
					{#each tags as tag (tag.id)}
						<span class="tag-pill" class:nsfw={tag.name.toLowerCase() === 'nsfw'}>
							{tag.name}
							<button class="tag-remove" onclick={() => removeTag(tag)} aria-label="Remove tag {tag.name}">×</button>
						</span>
					{/each}
				</div>
				<div class="tag-input-wrap">
					<input
						class="tag-input"
						type="text"
						placeholder="Add tag…"
						value={tagInput}
						oninput={onTagInput}
						onkeydown={onTagInputKeydown}
					/>
					{#if tagSuggestions.length > 0}
						<ul class="tag-suggestions">
							{#each tagSuggestions as suggestion (suggestion.id)}
								<li>
									<button onclick={() => selectTag(suggestion)}>
										{suggestion.name}
										{#if suggestion.name.toLowerCase() === 'nsfw'}<span class="nsfw-badge">NSFW</span>{/if}
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			</section>
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

	dt {
		color: #888;
		white-space: nowrap;
	}

	dd {
		margin: 0;
		color: #ccc;
		word-break: break-word;
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

	.tags-section {
		margin-top: 4px;
	}

	.tag-list {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 6px;
		min-height: 22px;
	}

	.tag-pill {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 6px;
		border-radius: 12px;
		background: #2d3e50;
		color: #8db4d8;
		font-size: 0.78rem;
		border: 1px solid #3a5570;
	}

	.tag-pill.nsfw {
		background: #4a1a1a;
		color: #e08080;
		border-color: #7a2a2a;
	}

	.tag-remove {
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: 0;
		font-size: 0.85rem;
		line-height: 1;
		opacity: 0.6;
	}

	.tag-remove:hover { opacity: 1; }

	.tag-input-wrap {
		position: relative;
	}

	.tag-input {
		width: 100%;
		padding: 4px 6px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		font-size: 0.82rem;
		box-sizing: border-box;
	}

	.tag-input:focus {
		outline: none;
		border-color: #6ea8fe;
	}

	.tag-suggestions {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		background: #252525;
		border: 1px solid #444;
		border-radius: 4px;
		list-style: none;
		margin: 2px 0 0;
		padding: 0;
		z-index: 10;
		max-height: 150px;
		overflow-y: auto;
	}

	.tag-suggestions li button {
		width: 100%;
		padding: 5px 8px;
		background: none;
		border: none;
		color: #ccc;
		font-size: 0.82rem;
		text-align: left;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.tag-suggestions li button:hover {
		background: #333;
	}

	.nsfw-badge {
		font-size: 0.7rem;
		padding: 1px 4px;
		border-radius: 3px;
		background: #7a2a2a;
		color: #e08080;
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
