import { readStored, removeStored, writeStored } from './storage';
import type { ImageSummary, MetadataMode, OverlayMode, SlideshowMode, SlideshowStatus } from './types';

export interface SlideshowConfig {
	interval: number;
	mode: SlideshowMode;
}

// ELO-weighted shuffle tuning (non-user-facing).
// Softmax temperature: ELO's natural ~400 scale means a 300-point gap ≈ 2.1×
// selection ratio. Lower = more biased toward high ELO.
const ELO_TEMPERATURE = 400;
// Weight multiplier applied to recently-shown images. Much less likely, but
// never zero — satisfies "chance shouldn't drop to zero".
const COOLDOWN_FACTOR = 0.05;
// Maximum number of recent slides kept in the recency window. The effective
// window is min(COOLDOWN_MAX, neighbors.length - 1).
const COOLDOWN_MAX = 20;
// How many shown slides ← can rewind through before the trail is trimmed.
const HISTORY_MAX = 500;

// Migrate the old `slideshow:shuffle` boolean to the new `slideshow:mode` value,
// then retire the legacy key so this runs at most once.
function readInitialMode(): SlideshowMode {
	const stored = readStored<SlideshowMode | null>('slideshow:mode', null);
	if (stored === 'sequential' || stored === 'random' || stored === 'elo') return stored;
	const legacy = readStored<boolean | null>('slideshow:shuffle', null);
	const mode: SlideshowMode = legacy === true ? 'random' : 'sequential';
	if (legacy !== null) {
		writeStored('slideshow:mode', mode);
		removeStored('slideshow:shuffle');
	}
	return mode;
}

function fisherYates(length: number, startIndex: number): number[] {
	const arr = Array.from({ length }, (_, i) => i);
	// Move startIndex to position 0
	[arr[0], arr[startIndex]] = [arr[startIndex], arr[0]];
	// Shuffle positions 1..length-1
	for (let i = length - 1; i > 1; i--) {
		const j = 1 + Math.floor(Math.random() * i);
		[arr[i], arr[j]] = [arr[j], arr[i]];
	}
	return arr;
}

function createSlideshowStore() {
	let status = $state<SlideshowStatus>('idle');
	let isFullscreen = $state(false);
	let pendingStart = $state(false);
	let config = $state<SlideshowConfig>({
		interval: readStored('slideshow:interval', 5000),
		mode: readInitialMode()
	});
	let metadataMode = $state<MetadataMode>(
		readStored('viewer:metadataMode', 'full' as MetadataMode)
	);
	let overlayMode = $state<OverlayMode>(
		readStored('slideshow:overlayMode', 'minimal' as OverlayMode)
	);

	// Internal runtime state (not reactive state — just bookkeeping)
	let neighbors: ImageSummary[] = [];
	let currentIndexRef = 0;
	let onAdvanceCb: ((hash: string) => void) | null = null;

	// ELO weighting: score map + whether the current context supports ELO.
	// "All Images" has no collection row, so ELO is unavailable there.
	let eloScores: Map<string, number> | null = null;
	let eloAvailable = false;

	// Remember the last non-sequential choice so ⇄ restores it (random or elo).
	let lastWeighted: 'random' | 'elo' =
		readStored<'random' | 'elo' | null>('slideshow:lastWeighted', null) ?? 'random';

	// random mode: precomputed permutation walked cyclically (no repeats per
	// cycle). elo mode: on-the-fly weighted draw with a recency cooldown.
	let shuffleOrder: number[] | null = null;
	let shufflePos = 0;

	// Ordered trail of neighbour indices shown this session, with a cursor.
	// → replays forward through it (drawing a fresh pick only at the tip) and
	// ← rewinds; it also feeds the elo recency window. Not used in sequential.
	let history: number[] = [];
	let historyPos = 0;

	let timerId: ReturnType<typeof setInterval> | null = null;

	function drawWeighted(): number {
		const n = neighbors.length;
		if (n === 1) return 0;

		// Base weights via softmax over ELO (missing scores default to 1500).
		let mean = 0;
		const scores: number[] = new Array(n);
		for (let i = 0; i < n; i++) {
			const s = eloScores?.get(neighbors[i].content_hash) ?? 1500;
			scores[i] = s;
			mean += s;
		}
		mean /= n;

		// Recency window: the last k shown slides are heavily suppressed but
		// not excluded. k is capped so tiny collections always have ≥1 free
		// candidate.
		const k = Math.max(1, Math.min(COOLDOWN_MAX, n - 1));
		const recent = new Set(history.slice(-k));

		const weights: number[] = new Array(n);
		let total = 0;
		for (let i = 0; i < n; i++) {
			let w = Math.exp((scores[i] - mean) / ELO_TEMPERATURE);
			if (recent.has(i)) w *= COOLDOWN_FACTOR;
			weights[i] = w;
			total += w;
		}

		if (!(total > 0)) return Math.floor(Math.random() * n);

		let r = Math.random() * total;
		for (let i = 0; i < n; i++) {
			r -= weights[i];
			if (r <= 0) return i;
		}
		return n - 1;
	}

	// The user's persisted `config.mode` is a preference; the mode actually
	// walked depends on the current context. `elo` degrades to `random` when
	// the context has no ELO scores (e.g. "All Images"), without touching the
	// stored preference — so it comes back on its own in a collection.
	function effectiveMode(): SlideshowMode {
		return config.mode === 'elo' && !eloAvailable ? 'random' : config.mode;
	}

	// Append a freshly drawn pick at the cursor, discarding any forward trail
	// left over from an earlier rewind and bounding the trail's length.
	function pushHistory(idx: number): void {
		history = history.slice(0, historyPos + 1);
		history.push(idx);
		if (history.length > HISTORY_MAX) history = history.slice(history.length - HISTORY_MAX);
		historyPos = history.length - 1;
	}

	// One step forward through the shuffle order: replay the visited trail if the
	// cursor is behind the tip, otherwise draw a new pick per the active mode.
	function stepForward(): number {
		if (historyPos < history.length - 1) {
			historyPos++;
		} else if (effectiveMode() === 'random') {
			// initOrder builds shuffleOrder whenever random is active; rebuild
			// defensively if it is ever missing.
			if (!shuffleOrder) shuffleOrder = fisherYates(neighbors.length, currentIndexRef);
			shufflePos = (shufflePos + 1) % shuffleOrder.length;
			pushHistory(shuffleOrder[shufflePos]);
		} else {
			pushHistory(drawWeighted());
		}
		return history[historyPos];
	}

	function advance() {
		if (!neighbors.length) return;

		if (effectiveMode() === 'sequential') {
			const nextIndex = currentIndexRef + 1;
			if (nextIndex >= neighbors.length) {
				// Stop at the end in sequential mode
				stop();
				return;
			}
			currentIndexRef = nextIndex;
		} else {
			currentIndexRef = stepForward();
		}

		onAdvanceCb?.(neighbors[currentIndexRef].content_hash);
	}

	// ← rewind: step back through the images actually shown this session. No-op
	// at the start of the trail; the page only calls it in shuffle modes.
	function back() {
		if (!neighbors.length || historyPos <= 0) return;
		historyPos--;
		currentIndexRef = history[historyPos];
		onAdvanceCb?.(neighbors[currentIndexRef].content_hash);
	}

	function stop() {
		if (timerId !== null) {
			clearInterval(timerId);
			timerId = null;
		}
	}

	function startTimer() {
		stop();
		timerId = setInterval(advance, config.interval);
	}

	// Halt the interval without changing play/pause status. Used while a video
	// slide plays so it isn't cut off; advance() is driven by the video ending.
	function suspendTimer() {
		stop();
	}

	function scheduleStart(): void {
		pendingStart = true;
	}

	function consumePendingStart(): boolean {
		if (pendingStart) {
			pendingStart = false;
			return true;
		}
		return false;
	}

	function initOrder(idx: number): void {
		shuffleOrder = null;
		shufflePos = 0;
		history = [idx];
		historyPos = 0;
		if (effectiveMode() === 'random') {
			shuffleOrder = fisherYates(neighbors.length, idx);
			shufflePos = 0;
		}
	}

	function enter(
		nbrs: ImageSummary[],
		idx: number,
		onAdvance: (hash: string) => void,
		opts?: { eloScores?: Map<string, number> | null; eloAvailable?: boolean }
	): void {
		neighbors = nbrs;
		currentIndexRef = idx;
		onAdvanceCb = onAdvance;
		eloScores = opts?.eloScores ?? null;
		eloAvailable = opts?.eloAvailable ?? false;

		// A persisted `elo` preference is honored as-is; `effectiveMode` (used by
		// `initOrder`/`advance`) transparently walks it as `random` when this
		// context has no ELO scores, so the preference survives the visit.
		initOrder(idx);

		status = 'playing';
		startTimer();
	}

	function exit(): void {
		stop();
		neighbors = [];
		currentIndexRef = 0;
		shuffleOrder = null;
		shufflePos = 0;
		history = [];
		historyPos = 0;
		eloScores = null;
		eloAvailable = false;
		onAdvanceCb = null;
		status = 'idle';

		if (isFullscreen && document.fullscreenElement) {
			document.exitFullscreen().catch(() => {});
		}
	}

	function play(): void {
		if (status === 'paused') {
			status = 'playing';
			startTimer();
		}
	}

	function pause(): void {
		if (status === 'playing') {
			status = 'paused';
			stop();
		}
	}

	function togglePlay(): void {
		if (status === 'playing') pause();
		else if (status === 'paused') play();
	}

	function resetTimer(): void {
		if (status === 'playing') {
			startTimer();
		}
	}

	// Sync the current index once the page settles on a new image. Navigation is
	// driven by advance()/back(), which own the shuffle order and history; this
	// just keeps the ref aligned with whatever is actually on screen.
	function updateCurrentIndex(idx: number): void {
		currentIndexRef = idx;
	}

	function setInterval_(ms: number): void {
		config = { ...config, interval: ms };
		writeStored('slideshow:interval', ms);
		if (status === 'playing') startTimer();
	}

	// ⇄ button: toggle shuffle on/off. Restores the last weighted choice
	// (random or elo) when turning back on.
	function toggleShuffle(): void {
		const next: SlideshowMode = config.mode === 'sequential' ? lastWeighted : 'sequential';
		setMode(next);
	}

	// ⚖ pill / e key: toggle ELO weighting. Turning it on also enables
	// shuffle (elo implies non-sequential); turning it off falls back to
	// plain random shuffle rather than all the way to sequential.
	function toggleWeighted(): void {
		if (!eloAvailable) return;
		if (config.mode === 'elo') setMode('random');
		else setMode('elo');
	}

	function setMode(mode: SlideshowMode): void {
		// Store the preference verbatim; `effectiveMode` handles ELO availability.
		if (mode === config.mode) return;
		config = { ...config, mode };
		writeStored('slideshow:mode', mode);
		if (mode === 'random' || mode === 'elo') {
			lastWeighted = mode;
			writeStored('slideshow:lastWeighted', mode);
		}
		// Rebuild the order/cooldown for the new strategy.
		if (neighbors.length) initOrder(currentIndexRef);
		if (status === 'playing') startTimer();
	}

	function setIsFullscreen(v: boolean): void {
		isFullscreen = v;
	}

	async function toggleFullscreen(el: HTMLElement): Promise<void> {
		if (document.fullscreenElement) {
			await document.exitFullscreen();
		} else {
			await el.requestFullscreen();
		}
	}

	function setMetadataMode(mode: MetadataMode): void {
		metadataMode = mode;
		writeStored('viewer:metadataMode', mode);
	}

	function setOverlayMode(mode: OverlayMode): void {
		overlayMode = mode;
		writeStored('slideshow:overlayMode', mode);
	}

	return {
		get status() { return status; },
		get isFullscreen() { return isFullscreen; },
		get pendingStart() { return pendingStart; },
		get config() { return config; },
		get eloAvailable() { return eloAvailable; },
		// True when ←/→ should walk the shuffle order/history rather than the
		// underlying collection order (i.e. any non-sequential effective mode).
		get isShuffle() { return effectiveMode() !== 'sequential'; },
		get metadataMode() { return metadataMode; },
		get overlayMode() { return overlayMode; },
		scheduleStart,
		consumePendingStart,
		enter,
		exit,
		play,
		pause,
		togglePlay,
		resetTimer,
		suspendTimer,
		advance,
		back,
		updateCurrentIndex,
		setInterval: setInterval_,
		toggleShuffle,
		toggleWeighted,
		setMode,
		setIsFullscreen,
		toggleFullscreen,
		setMetadataMode,
		setOverlayMode
	};
}

export const slideshowStore = createSlideshowStore();
