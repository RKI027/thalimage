import type { BrowsingContext } from './browsingContext';

/** Where the rankings page's back link goes: to voting when it was opened
 * from there (`from=vote`), else to the collection. */
export function rankingsBack(
	collectionId: number,
	name: string,
	from: string | null
): { href: string; label: string } {
	if (from === 'vote') return { href: `/elo/${collectionId}`, label: '← Voting' };
	return { href: `/collections/${collectionId}`, label: `← ${name}` };
}

/** The listing the viewer walks from the rankings page: the ranking itself,
 * from the top (the whole of it is the top 100%), with Back to `pageUrl`. */
export function rankingsContext(collectionId: number, name: string, pageUrl: string): BrowsingContext {
	return {
		type: 'collection',
		collectionId,
		name,
		sort: 'elo',
		dir: 'desc',
		filters: { elo_end: 'top', elo_percent: 100 },
		back: { href: pageUrl, label: 'Rankings' }
	};
}
