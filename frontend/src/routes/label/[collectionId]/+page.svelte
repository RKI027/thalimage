<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		addImageTag,
		createTag,
		getCollection,
		getCollectionLabels,
		listTags,
		previewUrl,
		removeImageTag
	} from '$lib/api';
	import { isTextEntry } from '$lib/keys';
	import {
		VOCABULARY,
		labelCounts,
		missingNamespaces,
		nextUnlabelled,
		toggleLabel,
		type ImageLabels
	} from '$lib/labels';
	import type { Collection } from '$lib/types';

	// Labelling a collection by hand: one image at a time, a button per
	// label with how many images of the collection carry it, so the rare
	// labels show.
	let collection: Collection | null = $state(null);
	let images: ImageLabels[] = $state([]);
	let index = $state(0);
	let error: string | null = $state(null);
	let busy = $state(false);
	const tagIds = new Map<string, number>();

	const current = $derived(images[index]);
	const counts = $derived(labelCounts(images));
	const missing = $derived(current ? missingNamespaces(VOCABULARY, current.labels) : []);
	const done = $derived(images.filter((i) => missingNamespaces(VOCABULARY, i.labels).length === 0).length);

	function collectionId(): number {
		return Number($page.params.collectionId);
	}

	$effect(() => {
		const _id = $page.params.collectionId;
		untrack(() => load(collectionId()));
	});

	async function load(id: number) {
		error = null;
		try {
			const [c, labelled, tags] = await Promise.all([
				getCollection(id),
				getCollectionLabels(id, VOCABULARY.map((n) => n.name)),
				listTags()
			]);
			for (const t of tags) tagIds.set(t.name, t.id);
			collection = c;
			images = labelled;
			const first = nextUnlabelled(VOCABULARY, images, images.length - 1);
			index = first === -1 ? 0 : first;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	}

	async function tagId(name: string): Promise<number> {
		let id = tagIds.get(name);
		if (id === undefined) {
			id = (await createTag(name)).id;
			tagIds.set(name, id);
		}
		return id;
	}

	async function toggle(label: string) {
		const image = current;
		if (!image || busy) return;
		const { add, remove } = toggleLabel(VOCABULARY, image.labels, label);
		busy = true;
		error = null;
		try {
			for (const name of remove) await removeImageTag(image.content_hash, await tagId(name));
			for (const name of add) await addImageTag(image.content_hash, await tagId(name));
			image.labels = [...image.labels.filter((l) => !remove.includes(l)), ...add].sort();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	function step(by: number) {
		if (images.length) index = (index + by + images.length) % images.length;
	}

	function skipToUnlabelled() {
		const next = nextUnlabelled(VOCABULARY, images, index);
		if (next !== -1) index = next;
	}

	function onKeydown(e: KeyboardEvent) {
		if (isTextEntry(e.target)) return;
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			step(1);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			step(-1);
		} else if (e.key === 'n') {
			e.preventDefault();
			skipToUnlabelled();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			goto(`/collections/${collectionId()}`);
		}
	}

	// Warm the next image's preview.
	$effect(() => {
		const next = images[(index + 1) % Math.max(images.length, 1)];
		if (next) new Image().src = previewUrl(next.content_hash);
	});
</script>

<svelte:window onkeydown={onKeydown} />

<div class="label-page">
	<div class="top-bar">
		<a href="/collections/{collectionId()}">← {collection?.name ?? 'Collection'}</a>
		<span class="progress">{done} of {images.length} labelled</span>
		<div class="actions">
			<button class="control" onclick={() => step(-1)} disabled={!images.length}>←</button>
			<span class="position">{images.length ? index + 1 : 0} / {images.length}</span>
			<button class="control" onclick={() => step(1)} disabled={!images.length}>→</button>
			<button class="control" onclick={skipToUnlabelled} title="Next image missing a label (n)">Next unlabelled</button>
		</div>
	</div>

	{#if error}
		<div class="error">{error}</div>
	{/if}

	{#if current}
		<div class="body">
			<a class="picture" href="/image/{current.content_hash}" title="Open in the viewer">
				<img src={previewUrl(current.content_hash)} alt="" />
			</a>
			<aside class="panel" class:busy>
				{#each VOCABULARY as ns (ns.name)}
					{@const most = Math.max(1, ...ns.values.map((v) => counts.get(`${ns.name}:${v}`) ?? 0))}
					<section>
						<h3 class:missing={missing.includes(ns.name)}>
							{ns.name}{ns.multiple ? ' (several)' : ''}
						</h3>
						<div class="values">
							{#each ns.values as value (value)}
								{@const label = `${ns.name}:${value}`}
								{@const count = counts.get(label) ?? 0}
								<button
									class="value"
									class:on={current.labels.includes(label)}
									onclick={() => toggle(label)}
									style="--share: {count / most}"
								>
									<span>{value}</span>
									<span class="count">{count}</span>
								</button>
							{/each}
						</div>
					</section>
				{/each}
				<p class="hint">← → step · n next unlabelled · Esc back</p>
			</aside>
		</div>
	{:else if !error}
		<div class="status">{images.length ? 'Loading…' : 'This collection has no images.'}</div>
	{/if}
</div>

<style>
	.label-page {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
	}

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: calc(8px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 8px
			max(16px, env(safe-area-inset-left));
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
		flex-wrap: wrap;
	}

	.progress,
	.position {
		color: #888;
		font-size: 0.85rem;
	}

	.actions {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.body {
		display: flex;
		flex: 1;
		min-height: 0;
	}

	.picture {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 0;
		position: relative;
		background: #000;
	}

	.picture img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: contain;
	}

	.panel {
		width: 360px;
		overflow-y: auto;
		padding: 12px;
		background: #1a1a1a;
		border-left: 1px solid #333;
	}

	.panel.busy {
		opacity: 0.6;
	}

	h3 {
		margin: 12px 0 6px;
		font-size: 0.8rem;
		text-transform: uppercase;
		color: #888;
	}

	h3.missing {
		color: #f0b050;
	}

	.values {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 3px;
	}

	.value {
		display: flex;
		justify-content: space-between;
		gap: 4px;
		padding: 5px 8px;
		border: 1px solid #333;
		font-size: 0.8rem;
		border-radius: 4px;
		color: #ccc;
		cursor: pointer;
		/* A bar behind the label, as long as its share of the namespace's
		   most common value: the short ones are the labels to look for. */
		background: linear-gradient(to right, #26324a calc(var(--share) * 100%), #222 0);
	}

	.value.on {
		border-color: #6fa0ff;
		color: #fff;
		font-weight: 600;
	}

	.count {
		color: #888;
	}

	.hint {
		margin-top: 16px;
		color: #666;
		font-size: 0.75rem;
	}

	.error {
		padding: 12px 16px;
		color: #f66;
	}

	.status {
		padding: 32px;
		text-align: center;
		color: #888;
	}

	@media (max-width: 768px) {
		.body {
			flex-direction: column;
		}

		.picture {
			flex: none;
			height: 50vh;
		}

		.panel {
			width: auto;
			border-left: none;
			border-top: 1px solid #333;
		}
	}
</style>
