<script lang="ts">
	import type * as PlotModule from '@observablehq/plot';
	import { getEloStats, thumbUrl } from '$lib/api';
	import { balancedBand, gini, headToHead, lorenz, matchCounts, showsImage } from '$lib/eloStats';
	import { settingsStore } from '$lib/stores';
	import type { CoveredImage, EloStats } from '$lib/types';
	import Chart from './Chart.svelte';

	let { collectionId }: { collectionId: number } = $props();

	// Chart colours, dark surface: one series hue, a blue↔red diverging pair
	// around a neutral gray, and the text inks (checked with the dataviz
	// palette validator against #1a1a1a).
	const SERIES = '#3987e5';
	const AGAINST = '#e66767';
	const NEUTRAL = '#383835';
	const INK = '#c3c2b7';
	const MUTED = '#898781';
	const UNPLAYED = '#242423';
	const TIP = { fill: '#111111', stroke: '#383835' };

	let stats = $state<EloStats | null>(null);
	let plot = $state<typeof PlotModule | null>(null);
	let error = $state<string | null>(null);

	type Cell = ReturnType<typeof headToHead>[number];
	/** The head-to-head cell under the pointer, and where the pointer is. */
	let matchup = $state<{ cell: Cell; x: number; y: number } | null>(null);
	const topById = $derived(new Map((stats?.top ?? []).map((t) => [t.content_hash, t])));

	$effect(() => {
		const id = collectionId;
		stats = null;
		error = null;
		Promise.all([getEloStats(id), import('@observablehq/plot')])
			.then(([s, p]) => {
				if (id !== collectionId) return;
				stats = s;
				plot = p;
			})
			.catch((e) => (error = e instanceof Error ? e.message : String(e)));
	});

	const matches = $derived(stats?.images.map((i) => i.matches) ?? []);
	const scored = $derived(stats?.images.filter((i): i is CoveredImage & { score: number; rank: number } => i.rank !== null) ?? []);
	const band = $derived(balancedBand(matches));
	const pairShare = $derived(stats && stats.pairs.possible > 0 ? stats.pairs.met / stats.pairs.possible : 0);

	function base(width: number, height = 240): PlotModule.PlotOptions {
		return { width, height, marginLeft: 48, marginTop: 24, marginBottom: 36, style: { background: 'transparent', fontSize: '12px' } };
	}

	const pct = (x: number) => `${(x * 100).toFixed(x < 0.1 && x > 0 ? 1 : 0)}%`;
	const count = (n: number) => n.toLocaleString();

	function matchHistogram(Plot: typeof PlotModule, width: number) {
		const counts = matchCounts(matches);
		const tallest = Math.max(1, ...counts.map((c) => c.images));
		return Plot.plot({
			...base(width),
			x: { label: 'Matches played →' },
			y: { label: '↑ Images', grid: true },
			marks: [
				Plot.rectY([band], { x1: (b) => b.low - 0.5, x2: (b) => b.high + 0.5, y1: 0, y2: tallest, fill: INK, fillOpacity: 0.08 }),
				Plot.text([band], { x: 'mean', frameAnchor: 'top', dy: -12, text: () => 'balanced', fill: MUTED }),
				Plot.rectY(counts, { x1: (d) => d.matches - 0.4, x2: (d) => d.matches + 0.4, y: 'images', fill: SERIES }),
				Plot.ruleY([0], { stroke: NEUTRAL }),
				Plot.tip(
					counts,
					Plot.pointerX({ x: 'matches', y: 'images', title: (d) => `${count(d.images)} images with ${d.matches} matches`, ...TIP })
				)
			]
		});
	}

	function lorenzCurve(Plot: typeof PlotModule, width: number) {
		const points = lorenz(matches);
		return Plot.plot({
			...base(width),
			x: { label: 'Share of images, least played first →', percent: true },
			y: { label: '↑ Share of matches', percent: true, grid: true },
			marks: [
				Plot.line([[0, 0], [1, 1]], { stroke: MUTED, strokeOpacity: 0.6 }),
				Plot.text([[0.62, 0.62]], { text: () => 'even', rotate: 0, dy: -8, fill: MUTED }),
				Plot.areaY(points, { x: 'images', y: 'matches', fill: SERIES, fillOpacity: 0.1 }),
				Plot.line(points, { x: 'images', y: 'matches', stroke: SERIES, strokeWidth: 2 }),
				Plot.tip(
					points,
					Plot.pointerX({ x: 'images', y: 'matches', title: (p) => `${pct(p.images)} of images played ${pct(p.matches)} of matches`, ...TIP })
				)
			]
		});
	}

	function matchesByRank(Plot: typeof PlotModule, width: number) {
		return Plot.plot({
			...base(width),
			x: { label: 'Rank →' },
			y: { label: '↑ Matches', grid: true },
			marks: [
				Plot.dot(scored, { x: 'rank', y: 'matches', fill: SERIES, r: 2.5, fillOpacity: 0.6 }),
				Plot.lineY(scored, Plot.binX<PlotModule.LineYOptions>({ y: 'mean' }, { x: 'rank', y: 'matches', thresholds: 20, stroke: INK, strokeWidth: 2 })),
				Plot.tip(
					scored,
					Plot.pointer({ x: 'rank', y: 'matches', title: (d) => `#${d.rank} · ${d.matches} matches\n${d.filename}`, ...TIP })
				)
			]
		});
	}

	function scoreHistogram(Plot: typeof PlotModule, width: number) {
		const bins = { x: 'score', thresholds: 30 } as const;
		return Plot.plot({
			...base(width),
			x: { label: 'Score →' },
			y: { label: '↑ Images', grid: true },
			marks: [
				Plot.rectY(scored, Plot.binX<PlotModule.RectYOptions>({ y: 'count' }, { ...bins, fill: SERIES, inset: 1 })),
				Plot.ruleX([1500], { stroke: INK, strokeOpacity: 0.7 }),
				Plot.text([1500], { x: (d) => d, frameAnchor: 'top', dy: -12, text: () => 'start', fill: MUTED }),
				Plot.ruleY([0], { stroke: NEUTRAL }),
				Plot.tip(scored, Plot.pointerX(Plot.binX<PlotModule.TipOptions>({ y: 'count' }, { ...bins, ...TIP })))
			]
		});
	}

	function confidenceFunnel(Plot: typeof PlotModule, width: number) {
		return Plot.plot({
			...base(width),
			x: { label: 'Matches played →' },
			y: { label: '↑ Score', grid: true },
			marks: [
				Plot.ruleY([1500], { stroke: INK, strokeOpacity: 0.7 }),
				Plot.dot(scored, { x: 'matches', y: 'score', fill: SERIES, r: 2.5, fillOpacity: 0.6 }),
				Plot.tip(
					scored,
					Plot.pointer({
						x: 'matches',
						y: 'score',
						title: (d) => `#${d.rank} · ${d.score.toFixed(0)} after ${d.matches} matches\n${d.filename}`,
						...TIP
					})
				)
			]
		});
	}

	function headToHeadGrid(Plot: typeof PlotModule, width: number) {
		const ids = (stats?.top ?? []).map((t) => t.content_hash);
		const label = (id: string) => `#${topById.get(id)?.rank}`;
		const cells = headToHead(ids, stats?.head_to_head ?? []);
		const played = cells.filter((c) => c.wins + c.losses > 0);
		const size = Math.min(width, 640);
		const grid = Plot.plot({
			width: size,
			height: size - 8,
			marginLeft: 40,
			marginTop: 32,
			style: { background: 'transparent', fontSize: '11px' },
			x: { domain: ids, tickFormat: label, axis: 'top', label: null },
			y: { domain: ids, tickFormat: label, label: null },
			color: {
				type: 'linear',
				domain: [0, 0.5, 1],
				range: [AGAINST, NEUTRAL, SERIES],
				legend: true,
				label: "Row's share of wins",
				tickFormat: '%'
			},
			marks: [
				Plot.cell(cells, { x: 'col', y: 'row', fill: UNPLAYED, inset: 1 }),
				Plot.cell(played, { x: 'col', y: 'row', fill: (c) => c.wins / (c.wins + c.losses), inset: 1 }),
				Plot.cell(cells, Plot.pointer({ x: 'col', y: 'row', fill: 'none', stroke: INK, strokeWidth: 1.5 }))
			]
		});
		let at = { x: 0, y: 0 };
		grid.addEventListener('pointermove', (e) => {
			const { clientX, clientY } = e as PointerEvent;
			at = { x: clientX, y: clientY };
			if (matchup) matchup = { ...matchup, ...at };
		});
		grid.addEventListener('input', () => {
			const cell = (grid as PlotModule.Plot).value as Cell | null;
			matchup = cell ? { cell, ...at } : null;
		});
		return grid;
	}

	/** Keeps the matchup card beside the pointer and inside the window. */
	function cardStyle(x: number, y: number): string {
		const left = x + 296 > innerWidth ? x - 296 : x + 16;
		const top = y + 220 > innerHeight ? y - 220 : y + 16;
		return `left: ${Math.max(8, left)}px; top: ${Math.max(8, top)}px`;
	}
</script>

{#if error}
	<div class="status error">{error}</div>
{:else if !stats || !plot}
	<div class="status">Loading…</div>
{:else if stats.images.length < 2}
	<div class="status">Voting needs at least two images in the collection.</div>
{:else}
	<div class="stats">
		<section>
			<h3>Match fairness</h3>
			<div class="tiles">
				<div class="tile"><span class="label">Gini coefficient</span><span class="value">{gini(matches).toFixed(2)}</span></div>
				<div class="tile"><span class="label">Average matches</span><span class="value">{band.mean.toFixed(1)}</span></div>
				<div class="tile">
					<span class="label">Never voted on</span>
					<span class="value">{count(stats.images.length - scored.length)}</span>
					<span class="sub">of {count(stats.images.length)} images</span>
				</div>
			</div>
			<div class="charts">
				<Chart {plot} title="Matches per image" note="Band: where a balanced schedule would put every image" render={matchHistogram} />
				<Chart {plot} title="Lorenz curve" note="Below the diagonal: matches go to some images more than others" render={lorenzCurve} />
				<Chart {plot} title="Matches by rank" note="Dots: images · line: average over each band of ranks" render={matchesByRank} />
			</div>
		</section>

		<section>
			<h3>Score and confidence</h3>
			<div class="charts">
				<Chart {plot} title="Scores" note="Every image starts at 1500" render={scoreHistogram} />
				<Chart {plot} title="Score against matches" note="Few matches: a score a few votes can still move far" render={confidenceFunnel} />
			</div>
		</section>

		<section>
			<h3>Pairs</h3>
			<div class="tiles">
				<div class="tile">
					<span class="label">Pairs met</span>
					<span class="value">{pct(pairShare)}</span>
					<span class="sub">{count(stats.pairs.met)} of {count(stats.pairs.possible)}</span>
				</div>
				<div class="tile"><span class="label">Met more than once</span><span class="value">{count(stats.pairs.repeated)}</span></div>
				<div class="tile"><span class="label">Most meetings of one pair</span><span class="value">{count(stats.pairs.most_meetings)}</span></div>
			</div>
			{#if stats.top.length >= 2}
				<div class="charts single">
					<Chart
						{plot}
						title="Head-to-head, top {stats.top.length}"
						note="Each cell: the row's record against the column · dark: never met"
						render={headToHeadGrid}
					/>
				</div>
			{/if}
			{#if matchup}
				{@const { cell } = matchup}
				<div class="matchup" style={cardStyle(matchup.x, matchup.y)} aria-hidden="true">
					{#each [cell.row, cell.col] as id, i (i)}
						{@const image = topById.get(id)}
						<div class="side">
							{#if image && showsImage(image, $settingsStore.show_nsfw)}
								<img src={thumbUrl(id)} alt="" />
							{:else}
								<div class="hidden-thumb">NSFW</div>
							{/if}
							<span class="who">#{image?.rank}</span>
							<span class="file">{image?.filename}</span>
						</div>
						{#if i === 0}
							<span class="record">{cell.wins + cell.losses ? `${cell.wins}–${cell.losses}` : 'never met'}</span>
						{/if}
					{/each}
				</div>
			{/if}
		</section>
	</div>
{/if}

<style>
	.stats {
		display: flex;
		flex-direction: column;
		gap: 24px;
		padding: 16px 0 calc(16px + env(safe-area-inset-bottom));
	}

	h3 {
		margin: 0 0 12px;
		font-size: 1rem;
		color: #f0efec;
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		max-width: 620px;
		gap: 12px;
		margin-bottom: 12px;
	}

	.tile {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 10px 14px;
		background: #1a1a1a;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
	}

	.label,
	.sub {
		color: #898781;
		font-size: 0.8rem;
	}

	.value {
		color: #f0efec;
		font-size: 1.5rem;
		font-weight: 600;
	}

	.charts {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
		gap: 12px;
		color: #c3c2b7;
	}

	.charts.single {
		grid-template-columns: minmax(0, 680px);
	}

	.matchup {
		position: fixed;
		z-index: 20;
		display: flex;
		align-items: center;
		gap: 10px;
		width: 280px;
		padding: 10px;
		background: #111111;
		border: 1px solid #383835;
		border-radius: 8px;
		pointer-events: none;
	}

	.side {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
	}

	.side img,
	.hidden-thumb {
		width: 110px;
		height: 110px;
		object-fit: cover;
		border-radius: 4px;
		background: #242423;
	}

	.hidden-thumb {
		display: flex;
		align-items: center;
		justify-content: center;
		color: #898781;
		font-size: 0.8rem;
	}

	.who {
		color: #f0efec;
		font-weight: 600;
		font-size: 0.85rem;
	}

	.file {
		max-width: 100%;
		color: #898781;
		font-size: 0.7rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.record {
		color: #c3c2b7;
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.status {
		padding: 32px;
		text-align: center;
		color: #888;
	}

	.error {
		color: #f66;
	}
</style>
