<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getEloRankings, getCollection, previewUrl, thumbUrl } from '$lib/api';
	import { EloRound } from '$lib/eloRound.svelte';
	import { collectionFiltersKey } from '$lib/gallery.svelte';
	import { readStored } from '$lib/storage';
	import { settingsStore } from '$lib/stores';
	import type { ImageSummary, EloRanking, Collection, FilterState } from '$lib/types';
	import SideBySideView from '$lib/components/views/SideBySideView.svelte';

	const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.avi']);

	let collection: Collection | null = $state(null);
	let showRankings = $state(false);
	let rankings: EloRanking[] = $state([]);

	const round = new EloRound(preload);

	function collectionId(): number {
		return Number($page.params.collectionId);
	}

	function preload(item: ImageSummary) {
		const ext = item.filename.slice(item.filename.lastIndexOf('.')).toLowerCase();
		const img = new Image();
		// Videos render from their thumbnail poster; warm that rather than fetching
		// the full video file through an <img>.
		img.src = VIDEO_EXTENSIONS.has(ext) ? thumbUrl(item.content_hash) : previewUrl(item.content_hash);
	}

	async function loadRankings() {
		rankings = await getEloRankings(collectionId());
		showRankings = true;
	}

	function onKeydown(e: KeyboardEvent) {
		if (showRankings) {
			if (e.key === 'Escape') {
				showRankings = false;
				e.preventDefault();
			}
			return;
		}
		if (e.key === 'ArrowLeft' || e.key === '1') {
			e.preventDefault();
			if (!e.repeat) round.vote('left');
		} else if (e.key === 'ArrowRight' || e.key === '2') {
			e.preventDefault();
			if (!e.repeat) round.vote('right');
		} else if (e.key === 's') {
			e.preventDefault();
			round.loadPair();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			goto(`/collections/${collectionId()}`);
		}
	}

	$effect(() => {
		const _id = $page.params.collectionId;
		const showNsfw = $settingsStore.show_nsfw;
		untrack(() => {
			const id = collectionId();
			round.setScope({
				collectionId: id,
				filters: readStored<FilterState>(collectionFiltersKey(id), {}),
				showNsfw
			});
			getCollection(id).then((c) => {
				if (id === collectionId()) collection = c;
			});
			round.loadPair();
		});
	});
</script>

<svelte:window onkeydown={onKeydown} />

<div class="elo-page">
	<div class="top-bar">
		<a href="/collections/{collectionId()}">← {collection?.name ?? 'Collection'}</a>
		<span class="vote-count">{round.voteCount} votes this session</span>
		<div class="actions">
			<button class="control" onclick={loadRankings}>Rankings</button>
			<button class="control" onclick={() => round.loadPair()}>Skip</button>
		</div>
	</div>

	{#if round.error}
		<div class="error">{round.error}</div>
	{:else if round.loading && !round.left}
		<div class="status">Loading…</div>
	{:else if round.left && round.right}
		{#if showRankings}
			<div class="rankings">
				<div class="rankings-header">
					<h3>Rankings</h3>
					<button class="control" onclick={() => (showRankings = false)}>Close</button>
				</div>
				{#if rankings.length === 0}
					<p class="empty">No votes recorded yet.</p>
				{:else}
					<ol>
						{#each rankings as r, i}
							<li>
								<span class="rank">#{i + 1}</span>
								<span class="name">{r.filename}</span>
								<span class="score">{r.score.toFixed(0)}</span>
								<span class="matches">{r.matches} matches</span>
							</li>
						{/each}
					</ol>
				{/if}
			</div>
		{:else}
			<SideBySideView
				left={round.left}
				right={round.right}
				selectedSide={round.selectedSide}
				onSelectLeft={() => round.vote('left')}
				onSelectRight={() => round.vote('right')}
			/>
			<div class="controls">
				<span class="hint desktop-hint">← or 1</span>
				<span class="hint mobile-hint">Tap top image</span>
				<span class="prompt">Which is better?</span>
				<span class="hint desktop-hint">→ or 2</span>
				<span class="hint mobile-hint">Tap bottom image</span>
			</div>
		{/if}
	{/if}
</div>

<style>
	.elo-page {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: calc(8px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 8px
			max(16px, env(safe-area-inset-left));
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.vote-count {
		color: #888;
		font-size: 0.85rem;
	}

	.actions {
		display: flex;
		gap: 8px;
	}

	.controls {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 24px;
		padding: 12px;
		background: #1a1a1a;
		border-top: 1px solid #333;
		flex-shrink: 0;
	}

	.prompt {
		color: #ccc;
		font-size: 1rem;
	}

	.hint {
		color: #666;
		font-size: 0.8rem;
	}

	.error {
		padding: 32px;
		text-align: center;
		color: #f66;
	}

	.status {
		padding: 32px;
		text-align: center;
		color: #888;
	}

	.rankings {
		flex: 1;
		padding: 16px;
		overflow-y: auto;
		overscroll-behavior-y: contain;
	}

	.rankings-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}

	.rankings-header h3 {
		margin: 0;
	}

	.empty {
		color: #666;
	}

	ol {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	ol li {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px;
		border-bottom: 1px solid #2a2a2a;
	}

	.rank {
		color: #888;
		min-width: 30px;
	}

	.name {
		flex: 1;
		color: #ccc;
	}

	.score {
		color: #6ea8fe;
		font-weight: 600;
		min-width: 50px;
		text-align: right;
	}

	.matches {
		color: #666;
		font-size: 0.8rem;
		min-width: 80px;
		text-align: right;
	}

	.mobile-hint {
		display: none;
	}

	@media (max-width: 768px) {
		.mobile-hint {
			display: inline;
		}

		.desktop-hint {
			display: none;
		}

		.top-bar {
			flex-wrap: wrap;
			gap: 8px;
		}

		.vote-count {
			width: 100%;
			text-align: center;
			order: 3;
			font-size: 0.75rem;
		}
	}
</style>
