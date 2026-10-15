<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getCollection, getEloRankings, thumbUrl } from '$lib/api';
	import { setBrowsingContext } from '$lib/browsingContext';
	import { rankingsBack, rankingsContext } from '$lib/rankings';
	import { settingsStore } from '$lib/stores';
	import type { Collection, EloRanked } from '$lib/types';

	const PAGE_SIZE = 100;

	let collection = $state<Collection | null>(null);
	let items: EloRanked[] = $state([]);
	let total = $state(0);
	let ranked = $state(0);
	let loading = $state(false);
	let error: string | null = $state(null);

	const collectionId = $derived(Number($page.params.id));
	const back = $derived(rankingsBack(collectionId, collection?.name ?? 'Collection', $page.url.searchParams.get('from')));

	async function load(offset: number) {
		const id = collectionId;
		loading = true;
		error = null;
		try {
			await settingsStore.loaded;
			const result = await getEloRankings(id, { offset, limit: PAGE_SIZE, showNsfw: $settingsStore.show_nsfw });
			if (id !== collectionId) return; // navigated on meanwhile
			items = offset === 0 ? result.items : [...items, ...result.items];
			total = result.total;
			ranked = result.ranked;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	function open(r: EloRanked) {
		if (!collection) return;
		setBrowsingContext(rankingsContext(collection.id, collection.name, $page.url.pathname + $page.url.search));
		goto(`/image/${r.image.content_hash}`);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			goto(back.href);
		}
	}

	$effect(() => {
		const id = collectionId;
		const _nsfw = $settingsStore.show_nsfw;
		untrack(() => {
			getCollection(id).then((c) => {
				if (id === collectionId) collection = c;
			});
			load(0);
		});
	});
</script>

<svelte:window onkeydown={onKeydown} />

<div class="rankings-page">
	<div class="top-bar">
		<a href={back.href}>{back.label}</a>
		<h2>{collection?.name ?? ''} — Rankings</h2>
		<span class="count">{ranked} ranked</span>
	</div>

	{#if error}
		<div class="status error">{error}</div>
	{:else if items.length === 0 && !loading}
		<div class="status">No votes recorded yet.</div>
	{:else}
		<div class="list">
		<ol class="ranking">
			{#each items as r (r.image.content_hash)}
				<li>
					<a
						href="/image/{r.image.content_hash}"
						class:archived={r.image.archived}
						onclick={(e) => {
							e.preventDefault();
							open(r);
						}}
					>
						<span class="rank">#{r.rank}</span>
						<img class="thumb" src={thumbUrl(r.image.content_hash)} alt="" loading="lazy" />
						<span class="name">
							{r.image.filename}
							{#if r.image.archived}<span class="tag">archived</span>{/if}
						</span>
						<span class="score">{r.score.toFixed(0)}</span>
						<span class="record" title="{r.matches} matches: {r.wins} won, {r.losses} lost">
							{r.wins}–{r.losses}
						</span>
					</a>
				</li>
			{/each}
		</ol>
		{#if items.length < total}
			<button class="control more" disabled={loading} onclick={() => load(items.length)}>
				{loading ? 'Loading…' : `Show more (${total - items.length} left)`}
			</button>
		{/if}
		</div>
	{/if}
</div>

<style>
	.rankings-page {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.top-bar {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: calc(8px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 8px
			max(16px, env(safe-area-inset-left));
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	h2 {
		margin: 0;
		font-size: 1.1rem;
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.count {
		color: #888;
		font-size: 0.85rem;
		white-space: nowrap;
	}

	.status {
		padding: 32px;
		text-align: center;
		color: #888;
	}

	.error {
		color: #f66;
	}

	.list {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		padding: 0 max(16px, env(safe-area-inset-right)) calc(16px + env(safe-area-inset-bottom))
			max(16px, env(safe-area-inset-left));
		overflow-y: auto;
		overscroll-behavior-y: contain;
	}

	.ranking {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.ranking a {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 6px 4px;
		border-bottom: 1px solid #2a2a2a;
		color: inherit;
		text-decoration: none;
	}

	.ranking a:hover {
		background: #222;
	}

	.ranking a.archived {
		opacity: 0.6;
	}

	.rank {
		color: #888;
		min-width: 3.5em;
		font-variant-numeric: tabular-nums;
	}

	.thumb {
		width: 48px;
		height: 48px;
		object-fit: cover;
		border-radius: 4px;
		background: #222;
		flex-shrink: 0;
	}

	.name {
		flex: 1;
		min-width: 0;
		color: #ccc;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.tag {
		margin-left: 6px;
		font-size: 0.75rem;
		color: #888;
	}

	.score {
		color: #6ea8fe;
		font-weight: 600;
		min-width: 3em;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.record {
		color: #888;
		font-size: 0.85rem;
		min-width: 4.5em;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.more {
		margin: 12px auto;
	}

	@media (max-width: 768px) {
		.top-bar {
			flex-wrap: wrap;
			gap: 8px;
		}

		.count {
			width: 100%;
			order: 3;
			font-size: 0.75rem;
		}

		.name {
			font-size: 0.85rem;
		}
	}
</style>
