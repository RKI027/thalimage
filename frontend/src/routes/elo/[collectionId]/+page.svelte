<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getEloPair, recordEloVote, getEloRankings, listCollections } from '$lib/api';
	import type { ImageSummary, EloRanking, Collection } from '$lib/types';
	import SideBySideView from '$lib/components/views/SideBySideView.svelte';

	let collection: Collection | null = $state(null);
	let left: ImageSummary | null = $state(null);
	let right: ImageSummary | null = $state(null);
	let selectedSide: 'left' | 'right' | null = $state(null);
	let voteCount = $state(0);
	let error: string | null = $state(null);
	let showRankings = $state(false);
	let rankings: EloRanking[] = $state([]);
	let loading = $state(false);

	function collectionId(): number {
		return Number($page.params.collectionId);
	}

	async function loadPair() {
		error = null;
		selectedSide = null;
		loading = true;
		try {
			const pair = await getEloPair(collectionId());
			left = pair.left;
			right = pair.right;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load pair';
		} finally {
			loading = false;
		}
	}

	async function vote(side: 'left' | 'right') {
		if (!left || !right) return;
		selectedSide = side;
		const winner = side === 'left' ? left.content_hash : right.content_hash;
		const loser = side === 'left' ? right.content_hash : left.content_hash;

		try {
			await recordEloVote(collectionId(), winner, loser);
			voteCount++;
			// Brief highlight before loading next pair
			setTimeout(() => loadPair(), 300);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to record vote';
		}
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
			vote('left');
		} else if (e.key === 'ArrowRight' || e.key === '2') {
			e.preventDefault();
			vote('right');
		} else if (e.key === 's') {
			e.preventDefault();
			loadPair();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			goto(`/collections/${collectionId()}`);
		}
	}

	$effect(() => {
		const _id = $page.params.collectionId;
		listCollections().then((colls) => {
			collection = colls.find((c) => c.id === collectionId()) ?? null;
		});
		loadPair();
	});
</script>

<svelte:window onkeydown={onKeydown} />

<div class="elo-page">
	<div class="top-bar">
		<a href="/collections/{collectionId()}">← {collection?.name ?? 'Collection'}</a>
		<span class="vote-count">{voteCount} votes this session</span>
		<div class="actions">
			<button onclick={loadRankings}>Rankings</button>
			<button onclick={() => loadPair()}>Skip</button>
		</div>
	</div>

	{#if error}
		<div class="error">{error}</div>
	{:else if loading && !left}
		<div class="status">Loading…</div>
	{:else if left && right}
		{#if showRankings}
			<div class="rankings">
				<div class="rankings-header">
					<h3>Rankings</h3>
					<button onclick={() => (showRankings = false)}>Close</button>
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
				{left}
				{right}
				{selectedSide}
				onSelectLeft={() => vote('left')}
				onSelectRight={() => vote('right')}
			/>
			<div class="controls">
				<span class="hint">← or 1</span>
				<span class="prompt">Which is better?</span>
				<span class="hint">→ or 2</span>
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
		padding: 8px 16px;
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

	.actions button {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
	}

	.actions button:hover {
		background: #3a3a3a;
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

	.rankings-header button {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
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
</style>
