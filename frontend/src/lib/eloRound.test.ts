import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EloPair } from './types';

const getEloPair = vi.fn();
const recordEloVote = vi.fn();
vi.mock('./api', () => ({
	getEloPair: (...a: unknown[]) => getEloPair(...a),
	recordEloVote: (...a: unknown[]) => recordEloVote(...a)
}));

const { EloRound } = await import('./eloRound.svelte');

function pair(l: string, r: string): EloPair {
	return {
		left: { content_hash: l } as EloPair['left'],
		right: { content_hash: r } as EloPair['right']
	};
}

function deferred<T>() {
	let resolve!: (v: T) => void;
	const promise = new Promise<T>((r) => (resolve = r));
	return { promise, resolve };
}

const flush = () => new Promise((r) => setTimeout(r, 0));
const scope = (collectionId: number) => ({ collectionId, filters: {}, showNsfw: false });

describe('EloRound', () => {
	beforeEach(() => {
		getEloPair.mockReset();
		recordEloVote.mockReset();
		vi.useRealTimers();
	});

	it('shows the prefetched pair next', async () => {
		const round = new EloRound();
		getEloPair.mockResolvedValueOnce(pair('a', 'b')).mockResolvedValueOnce(pair('c', 'd'));
		round.setScope(scope(1));
		await round.loadPair();
		await flush();
		getEloPair.mockResolvedValue(pair('e', 'f'));
		await round.loadPair();
		expect([round.left?.content_hash, round.right?.content_hash]).toEqual(['c', 'd']);
	});

	it('records one vote per pair however often it is asked (GEN-009)', async () => {
		vi.useFakeTimers();
		const round = new EloRound();
		getEloPair.mockResolvedValue(pair('a', 'b'));
		round.setScope(scope(1));
		await round.loadPair();
		const posted = deferred<unknown>();
		recordEloVote.mockReturnValue(posted.promise);

		const first = round.vote('left');
		round.vote('left'); // key repeat
		round.vote('right'); // double tap on the other side
		posted.resolve({ status: 'recorded' });
		await first;

		expect(recordEloVote).toHaveBeenCalledOnce();
		expect(recordEloVote).toHaveBeenCalledWith(1, 'a', 'b');
		expect(round.voteCount).toBe(1);
	});

	it('lets the user retry after a failed vote', async () => {
		const round = new EloRound();
		getEloPair.mockResolvedValue(pair('a', 'b'));
		round.setScope(scope(1));
		await round.loadPair();
		recordEloVote.mockRejectedValueOnce(new Error('offline'));
		await round.vote('left');
		expect(round.error).toBe('offline');
		recordEloVote.mockResolvedValueOnce({ status: 'recorded' });
		await round.vote('left');
		expect(recordEloVote).toHaveBeenCalledTimes(2);
	});

	it('drops a prefetch that lands after a collection switch (GEN-015)', async () => {
		const round = new EloRound();
		const lateA = deferred<EloPair>();
		getEloPair.mockResolvedValueOnce(pair('a1', 'a2')).mockReturnValueOnce(lateA.promise);
		round.setScope(scope(1));
		await round.loadPair(); // starts collection 1's prefetch

		getEloPair.mockResolvedValueOnce(pair('b1', 'b2'));
		round.setScope(scope(2));
		const loadB = round.loadPair();
		lateA.resolve(pair('a3', 'a4')); // collection 1's prefetch arrives late
		await loadB;
		await flush();

		getEloPair.mockResolvedValue(pair('b3', 'b4'));
		await round.loadPair();
		expect([round.left?.content_hash, round.right?.content_hash]).toEqual(['b3', 'b4']);
	});

	it('drops a live pair that lands after a collection switch', async () => {
		const round = new EloRound();
		const lateA = deferred<EloPair>();
		getEloPair.mockReturnValueOnce(lateA.promise);
		round.setScope(scope(1));
		const loadA = round.loadPair();

		getEloPair.mockResolvedValue(pair('b1', 'b2'));
		round.setScope(scope(2));
		await round.loadPair();
		lateA.resolve(pair('a1', 'a2'));
		await loadA;
		expect(round.left?.content_hash).toBe('b1');
	});
});
