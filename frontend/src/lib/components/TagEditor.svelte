<script lang="ts">
	import { addImageTag, createTag, getImageTags, listTags, removeImageTag } from '$lib/api';
	import type { Tag } from '$lib/types';

	/** The tags of the image keyed `hash`, editable: each change applies at
	 * once. `folderTags` are shown, read-only. `onchange` gets the tags after
	 * each change. */
	let {
		hash,
		folderTags = [],
		onchange
	}: { hash: string; folderTags?: string[]; onchange?: (tags: Tag[]) => void } = $props();

	let tags = $state<Tag[]>([]);
	let tagInput = $state('');
	let tagSuggestions = $state<Tag[]>([]);
	let tagInputDebounce: ReturnType<typeof setTimeout> | null = null;

	function setTags(next: Tag[]) {
		tags = next;
		onchange?.(next);
	}

	$effect(() => {
		const shown = hash;
		getImageTags(shown).then((t) => {
			if (shown === hash) setTags(t);
		});
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
		await addImageTag(hash, tag.id);
		setTags(await getImageTags(hash));
		tagInput = '';
		tagSuggestions = [];
	}

	async function addNewTag(name: string) {
		const tag = await createTag(name.trim());
		await addImageTag(hash, tag.id);
		setTags(await getImageTags(hash));
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
		await removeImageTag(hash, tag.id);
		setTags(tags.filter((t) => t.id !== tag.id));
	}
</script>

	<div class="tag-list">
		{#each folderTags as name (name)}
			<span class="tag-pill folder" title="From where the file is; changes when it moves">{name}</span>
		{/each}
		{#each tags as tag (tag.id)}
			<span class="tag-pill" class:nsfw={tag.name.toLowerCase() === 'nsfw'}>
				{tag.name}
				<button class="tag-remove" onclick={() => removeTag(tag)} aria-label="Remove tag {tag.name}">×</button>
			</span>
		{/each}
	</div>
	<div class="tag-input-wrap">
		<input
			class="control tag-input"
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

<style>
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

	.tag-pill.folder {
		background: none;
		border-style: dashed;
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
</style>
