/** Figures the voting statistics derive from match counts and meetings. */

import type { Meeting } from './types';

/** How unevenly matches spread over images: 0 when every image has played
 * as often as every other, approaching 1 when a few have played them all. */
export function gini(matches: number[]): number {
	const n = matches.length;
	const total = matches.reduce((a, b) => a + b, 0);
	if (n === 0 || total === 0) return 0;
	const sorted = [...matches].sort((a, b) => a - b);
	const weighted = sorted.reduce((acc, m, i) => acc + (i + 1) * m, 0);
	return (2 * weighted) / (n * total) - (n + 1) / n;
}

/** The Lorenz curve: the share of all matches played by the least-played
 * share of images, from (0, 0) to (1, 1). With no matches, the diagonal. */
export function lorenz(matches: number[]): { images: number; matches: number }[] {
	const n = matches.length;
	const total = matches.reduce((a, b) => a + b, 0);
	const sorted = [...matches].sort((a, b) => a - b);
	const points = [{ images: 0, matches: 0 }];
	let running = 0;
	sorted.forEach((m, i) => {
		running += m;
		points.push({ images: (i + 1) / n, matches: total === 0 ? (i + 1) / n : running / total });
	});
	return points;
}

/** Where a balanced schedule would put every image: within one match of
 * the average, so between the whole numbers around it. */
export function balancedBand(matches: number[]): { mean: number; low: number; high: number } {
	const mean = matches.reduce((a, b) => a + b, 0) / matches.length;
	return { mean, low: Math.floor(mean), high: Math.ceil(mean) };
}

/** How many images have played each number of matches, from 0 to the most. */
export function matchCounts(matches: number[]): { matches: number; images: number }[] {
	const most = Math.max(0, ...matches);
	const counts = Array.from({ length: most + 1 }, (_, k) => ({ matches: k, images: 0 }));
	for (const m of matches) counts[m].images++;
	return counts;
}

/** Each ordered pair of distinct images in `top`: the row's wins and
 * losses against the column. */
export function headToHead(
	top: string[],
	meetings: Meeting[]
): { row: string; col: string; wins: number; losses: number }[] {
	const won = new Map(meetings.map((m) => [`${m.winner}|${m.loser}`, m.count]));
	return top.flatMap((row) =>
		top
			.filter((col) => col !== row)
			.map((col) => ({ row, col, wins: won.get(`${row}|${col}`) ?? 0, losses: won.get(`${col}|${row}`) ?? 0 }))
	);
}
