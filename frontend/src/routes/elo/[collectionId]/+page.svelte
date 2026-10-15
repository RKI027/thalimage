<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getCollection, previewUrl, thumbUrl } from '$lib/api';
	import { eloCutLabel } from '$lib/eloCut';
	import { EloRound } from '$lib/eloRound.svelte';
	import { collectionFiltersKey } from '$lib/gallery.svelte';
	import { isVideoFilename } from '$lib/media';
	import { readStored } from '$lib/storage';
	import { settingsStore } from '$lib/stores';
	import type { ImageSummary, Collection, FilterState } from '$lib/types';
	import SideBySideView from '$lib/components/views/SideBySideView.svelte';

	let collection: Collection | null = $state(null);
	let filters: FilterState = $state({});
	const cutLabel = $derived(eloCutLabel(filters));

	const round = new EloRound(preload);

	function collectionId(): number {
		return Number($page.params.collectionId);
	}

	function preload(item: ImageSummary) {
		const img = new Image();
		// Videos render from their thumbnail poster; warm that rather than fetching
		// the full video file through an <img>.
		img.src = isVideoFilename(item.filename) ? thumbUrl(item.content_hash) : previewUrl(item.content_hash);
	}

	function onKeydown(e: KeyboardEvent) {
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
			filters = readStored<FilterState>(collectionFiltersKey(id), {});
			round.setScope({ collectionId: id, filters, showNsfw });
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
		<span class="vote-count">
			{round.voteCount} votes this session
			{#if cutLabel}
				<span class="cut" title="Pairs come from this part of the ranking only, as the collection's ELO filter sets">ELO: {cutLabel}</span>
			{/if}
		</span>
		<div class="actions">
			<a class="control" href="/collections/{collectionId()}/rankings?from=vote">Rankings</a>
			<button class="control" onclick={() => round.loadPair()}>Skip</button>
		</div>
	</div>

	{#if round.error}
		<div class="error">{round.error}</div>
	{:else if round.loading && !round.left}
		<div class="status">Loading…</div>
	{:else if round.left && round.right}
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

	.cut {
		margin-left: 8px;
		padding: 2px 8px;
		border-radius: 10px;
		background: #2a3a55;
		color: #9ec0ff;
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
