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

export type RankingsView = 'list' | 'stats';

/** The tab a `view` parameter names; the stats are the default. */
export function rankingsView(param: string | null): RankingsView {
	return param === 'list' ? 'list' : 'stats';
}

/** The rankings page at `pathname` showing `view`, other parameters of
 * `search` kept; the stats are the default and need no parameter. */
export function rankingsViewHref(pathname: string, search: string, view: RankingsView): string {
	const q = new URLSearchParams(search);
	if (view === rankingsView(null)) q.delete('view');
	else q.set('view', view);
	const qs = q.toString();
	return qs ? `${pathname}?${qs}` : pathname;
}
