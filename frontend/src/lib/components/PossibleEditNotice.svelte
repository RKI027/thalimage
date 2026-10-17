<script lang="ts">
	import { thumbUrl } from '$lib/api';
	import type { PossibleEdit, PossibleEditDecision } from '$lib/types';

	/**
	 * Asks whether the image is an edit of the earlier picture that was at
	 * its path: merging gives it that picture's tags, votes, scores and
	 * collections; keeping them separate is not asked again.
	 */
	let {
		edit,
		ondecide
	}: {
		edit: PossibleEdit;
		ondecide: (decision: PossibleEditDecision) => Promise<void>;
	} = $props();

	let busy = $state(false);
	let message = $state('');

	async function decide(decision: PossibleEditDecision) {
		busy = true;
		message = '';
		try {
			await ondecide(decision);
		} catch (e) {
			message = e instanceof Error ? e.message : 'Could not save the decision';
		} finally {
			busy = false;
		}
	}
</script>

<div class="notice" role="region" aria-label="Possible edit">
	<img src={thumbUrl(edit.old_hash)} alt="Earlier version at this path" />
	<div class="text">
		<p>
			An edit of this earlier picture, which was at the same path?
			<span class="distance">{Math.round(edit.distance * 100)}% different</span>
		</p>
		{#if message}
			<p class="message">{message}</p>
		{/if}
		<div class="actions">
			<button
				class="control"
				disabled={busy}
				onclick={() => decide('merge')}
				title="Keep one image: this one takes the earlier picture's tags, votes, scores and collections"
			>
				Merge
			</button>
			<button class="control" disabled={busy} onclick={() => decide('separate')} title="Keep two images; not asked again">
				Keep separate
			</button>
		</div>
	</div>
</div>

<style>
	.notice {
		position: absolute;
		left: 12px;
		bottom: calc(72px + env(safe-area-inset-bottom));
		z-index: 11;
		display: flex;
		gap: 12px;
		max-width: min(420px, calc(100vw - 24px));
		padding: 10px;
		border: 1px solid #444;
		border-radius: 6px;
		background: rgba(30, 30, 30, 0.95);
		color: #ddd;
		font-size: 0.85rem;
	}

	img {
		width: 72px;
		height: 72px;
		object-fit: cover;
		border-radius: 4px;
		flex: none;
	}

	p {
		margin: 0 0 8px;
	}

	.distance {
		color: #999;
		white-space: nowrap;
	}

	.message {
		color: #e88;
	}

	.actions {
		display: flex;
		gap: 8px;
	}
</style>
