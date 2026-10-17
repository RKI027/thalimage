import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EloPair } from './types';

const getEloPair = vi.fn();
const recordEloVote = vi.fn();
const archiveImage = vi.fn();
vi.mock('./api', () => ({
	getEloPair: (...a: unknown[]) => getEloPair(...a),
	recordEloVote: (...a: unknown[]) => recordEloVote(...a),
	archiveImage: (...a: unknown[]) => archiveImage(...a)
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
		archiveImage.mockReset();
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

	it('keeps the pair on screen out of the next one', async () => {
		const round = new EloRound();
		getEloPair.mockResolvedValueOnce(pair('a', 'b')).mockResolvedValueOnce(pair('c', 'd'));
		round.setScope(scope(1));
		await round.loadPair();
		await flush();
		expect(getEloPair).toHaveBeenNthCalledWith(1, 1, {}, false, []);
		expect(getEloPair).toHaveBeenNthCalledWith(2, 1, {}, false, ['a', 'b']);
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

	it('archives one side and moves on without a vote', async () => {
		const round = new EloRound();
		getEloPair.mockResolvedValueOnce(pair('a', 'b')).mockResolvedValueOnce(pair('c', 'd'));
		round.setScope(scope(1));
		await round.loadPair();
		await flush();
		archiveImage.mockResolvedValue({});

		await round.archive('right');

		expect(archiveImage).toHaveBeenCalledOnce();
		expect(archiveImage).toHaveBeenCalledWith('b', true);
		expect(recordEloVote).not.toHaveBeenCalled();
		expect(round.voteCount).toBe(0);
		expect([round.left?.content_hash, round.right?.content_hash]).toEqual(['c', 'd']);
	});

	it('archives once however often it is asked, and blocks a vote meanwhile', async () => {
		const round = new EloRound();
		getEloPair.mockResolvedValue(pair('a', 'b'));
		round.setScope(scope(1));
		await round.loadPair();
		const archived = deferred<unknown>();
		archiveImage.mockReturnValue(archived.promise);

		const first = round.archive('left');
		round.archive('left');
		round.vote('right');
		archived.resolve({});
		await first;

		expect(archiveImage).toHaveBeenCalledOnce();
		expect(recordEloVote).not.toHaveBeenCalled();
	});

	it('keeps the pair after a failed archive so the user can retry', async () => {
		const round = new EloRound();
		getEloPair.mockResolvedValue(pair('a', 'b'));
		round.setScope(scope(1));
		await round.loadPair();
		archiveImage.mockRejectedValueOnce(new Error('offline'));
		await round.archive('left');
		expect(round.error).toBe('offline');
		expect(round.left?.content_hash).toBe('a');
		archiveImage.mockResolvedValueOnce({});
		await round.archive('left');
		expect(archiveImage).toHaveBeenCalledTimes(2);
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
