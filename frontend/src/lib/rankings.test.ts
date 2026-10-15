import { describe, expect, it } from 'vitest';
import { rankingsBack, rankingsContext, rankingsViewHref } from './rankings';

describe('rankingsBack', () => {
	it('returns to voting when opened from there', () => {
		expect(rankingsBack(4, 'Cats', 'vote')).toEqual({ href: '/elo/4', label: '← Voting' });
	});

	it('returns to the collection otherwise', () => {
		expect(rankingsBack(4, 'Cats', null)).toEqual({ href: '/collections/4', label: '← Cats' });
	});
});

describe('rankingsContext', () => {
	it('walks the whole ranking from the top, and comes back to the page', () => {
		expect(rankingsContext(4, 'Cats', '/collections/4/rankings?from=vote')).toEqual({
			type: 'collection',
			collectionId: 4,
			name: 'Cats',
			sort: 'elo',
			dir: 'desc',
			filters: { elo_end: 'top', elo_percent: 100 },
			back: { href: '/collections/4/rankings?from=vote', label: 'Rankings' }
		});
	});
});

describe('rankingsViewHref', () => {
	it('switches tab, keeping where the page was opened from', () => {
		expect(rankingsViewHref('/collections/4/rankings', '?from=vote', 'stats')).toBe(
			'/collections/4/rankings?from=vote&view=stats'
		);
		expect(rankingsViewHref('/collections/4/rankings', '?from=vote&view=stats', 'list')).toBe(
			'/collections/4/rankings?from=vote'
		);
	});
});
