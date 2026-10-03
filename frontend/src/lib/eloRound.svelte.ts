/**
 * The ELO page's state: the pair on screen, the one prefetched behind it,
 * and the vote in progress. Every request is tagged with the scope it was
 * made for (collection, filters, NSFW switch); a response for any other
 * scope is dropped, so nothing from a previous collection can surface.
 */
import { getEloPair, recordEloVote } from './api';
import type { EloPair, FilterState, ImageSummary } from './types';

/** How long the chosen side stays highlighted before the next pair. */
const HIGHLIGHT_MS = 300;

interface Scope {
	collectionId: number;
	filters: FilterState;
	showNsfw: boolean;
}

export class EloRound {
	left = $state<ImageSummary | null>(null);
	right = $state<ImageSummary | null>(null);
	selectedSide = $state<'left' | 'right' | null>(null);
	voteCount = $state(0);
	error = $state<string | null>(null);
	loading = $state(false);

	#scope: Scope | null = null;
	#scopeKey = '';
	#next: { key: string; pair: EloPair } | null = null;
	#preload: (item: ImageSummary) => void;

	constructor(preload: (item: ImageSummary) => void = () => {}) {
		this.#preload = preload;
	}

	/** Switch collection or filters; forgets the prefetched pair. */
	setScope(scope: Scope): void {
		this.#scope = scope;
		this.#scopeKey = JSON.stringify(scope);
		this.#next = null;
	}

	async loadPair(): Promise<void> {
		const scope = this.#scope;
		if (!scope) return;
		const key = this.#scopeKey;
		this.error = null;
		this.selectedSide = null;

		const next = this.#next;
		this.#next = null;
		if (next?.key === key) {
			this.left = next.pair.left;
			this.right = next.pair.right;
			this.#prefetch();
			return;
		}

		this.loading = true;
		try {
			const pair = await getEloPair(scope.collectionId, scope.filters, scope.showNsfw);
			if (key !== this.#scopeKey) return;
			this.left = pair.left;
			this.right = pair.right;
		} catch (e) {
			if (key === this.#scopeKey) this.error = e instanceof Error ? e.message : 'Failed to load pair';
			return;
		} finally {
			if (key === this.#scopeKey) this.loading = false;
		}
		this.#prefetch();
	}

	/** Record a vote for one side. Ignored while a vote is already under way,
	 * so a repeated key or a double tap counts once. */
	async vote(side: 'left' | 'right'): Promise<void> {
		const scope = this.#scope;
		if (!scope || !this.left || !this.right || this.selectedSide !== null) return;
		const key = this.#scopeKey;
		this.selectedSide = side;
		const [winner, loser] = side === 'left' ? [this.left, this.right] : [this.right, this.left];
		try {
			await recordEloVote(scope.collectionId, winner.content_hash, loser.content_hash);
		} catch (e) {
			if (key === this.#scopeKey) {
				this.error = e instanceof Error ? e.message : 'Failed to record vote';
				this.selectedSide = null;
			}
			return;
		}
		if (key !== this.#scopeKey) return;
		this.voteCount++;
		setTimeout(() => {
			if (key === this.#scopeKey) this.loadPair();
		}, HIGHLIGHT_MS);
	}

	async #prefetch(): Promise<void> {
		const scope = this.#scope;
		if (!scope) return;
		const key = this.#scopeKey;
		try {
			const pair = await getEloPair(scope.collectionId, scope.filters, scope.showNsfw);
			if (key !== this.#scopeKey) return;
			this.#preload(pair.left);
			this.#preload(pair.right);
			this.#next = { key, pair };
		} catch {
			// Best-effort: the next round just fetches live.
		}
	}
}
