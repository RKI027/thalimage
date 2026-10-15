import { readStored, removeStored, writeStored } from './storage';
import type { MetadataMode, OverlayMode, SequenceItem, SlideshowMode, SlideshowStatus } from './types';

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
// window is min(COOLDOWN_MAX, items.length - 1).
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

	// The listing walked, and the index in it of the image shown.
	let items = $state.raw<SequenceItem[]>([]);
	let current = $state(0);

	// Internal runtime state (not reactive state — just bookkeeping)
	let onAdvanceCb: ((hash: string) => void) | null = null;

	// ELO weighting is available where the items carry scores: in a
	// collection. "All Images" has no collection row, so ELO is unavailable there.
	let eloAvailable = false;

	// Remember the last non-sequential choice so ⇄ restores it (random or elo).
	let lastWeighted: 'random' | 'elo' =
		readStored<'random' | 'elo' | null>('slideshow:lastWeighted', null) ?? 'random';

	// random mode: precomputed permutation walked cyclically (no repeats per
	// cycle). elo mode: on-the-fly weighted draw with a recency cooldown.
	let shuffleOrder: number[] | null = null;
	let shufflePos = 0;

	// Picks drawn past the tip of the trail, so the next slides are known
	// (and can be preloaded) before they are shown.
	let ahead: number[] = [];

	// Ordered trail of listing indices shown this session, with a cursor.
	// → replays forward through it (drawing a fresh pick only at the tip) and
	// ← rewinds; it also feeds the elo recency window. Not used in sequential.
	let history: number[] = [];
	let historyPos = 0;

	let timerId: ReturnType<typeof setInterval> | null = null;

	function drawWeighted(): number {
		const n = items.length;
		if (n === 1) return 0;

		// Base weights via softmax over ELO (missing scores default to 1500).
		let mean = 0;
		const scores: number[] = new Array(n);
		for (let i = 0; i < n; i++) {
			const s = items[i].score ?? 1500;
			scores[i] = s;
			mean += s;
		}
		mean /= n;

		// Recency window: the last k slides shown or drawn ahead are heavily
		// suppressed but not excluded. k is capped so tiny collections always
		// have ≥1 free candidate.
		const k = Math.max(1, Math.min(COOLDOWN_MAX, n - 1));
		const recent = new Set([...history, ...ahead].slice(-k));

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

	// Draw picks onto `ahead` until it holds n, per the active shuffle mode.
	function fillAhead(n: number): void {
		while (ahead.length < n) {
			if (effectiveMode() === 'random') {
				// initOrder builds shuffleOrder whenever random is active; rebuild
				// defensively if it is ever missing.
				if (!shuffleOrder) shuffleOrder = fisherYates(items.length, current);
				shufflePos = (shufflePos + 1) % shuffleOrder.length;
				ahead.push(shuffleOrder[shufflePos]);
			} else {
				ahead.push(drawWeighted());
			}
		}
	}

	// One step forward through the shuffle order: replay the visited trail if the
	// cursor is behind the tip, otherwise take the next pick drawn ahead.
	function stepForward(): number {
		if (historyPos < history.length - 1) {
			historyPos++;
		} else {
			fillAhead(1);
			pushHistory(ahead.shift()!);
		}
		return history[historyPos];
	}

	function advance() {
		if (!items.length) return;

		if (effectiveMode() === 'sequential') {
			const nextIndex = current + 1;
			if (nextIndex >= items.length) {
				// Stop at the end in sequential mode
				stop();
				return;
			}
			current = nextIndex;
		} else {
			current = stepForward();
		}

		onAdvanceCb?.(items[current].content_hash);
	}

	// ←: rewind through the images actually shown this session in shuffle
	// modes, or step to the previous image of the listing in sequential.
	// No-op at the start.
	function back() {
		if (!items.length) return;
		if (effectiveMode() === 'sequential') {
			if (current <= 0) return;
			current--;
		} else {
			if (historyPos <= 0) return;
			historyPos--;
			current = history[historyPos];
		}
		onAdvanceCb?.(items[current].content_hash);
	}

	// The next n slides advance() will show, nearest first.
	function upcoming(n: number): SequenceItem[] {
		if (!items.length) return [];
		if (effectiveMode() === 'sequential') return items.slice(current + 1, current + 1 + n);
		const trail = history.slice(historyPos + 1, historyPos + 1 + n);
		const drawn = n - trail.length;
		fillAhead(drawn);
		return [...trail, ...ahead.slice(0, drawn)].map((i) => items[i]);
	}

	// The last n slides back() returns to, nearest first.
	function recent(n: number): SequenceItem[] {
		if (effectiveMode() === 'sequential') return items.slice(Math.max(0, current - n), current).reverse();
		return history
			.slice(Math.max(0, historyPos - n), historyPos)
			.reverse()
			.map((i) => items[i]);
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
		ahead = [];
		history = [idx];
		historyPos = 0;
		if (effectiveMode() === 'random') {
			shuffleOrder = fisherYates(items.length, idx);
			shufflePos = 0;
		}
	}

	function enter(listing: SequenceItem[], idx: number, onAdvance: (hash: string) => void): void {
		items = listing;
		current = idx;
		onAdvanceCb = onAdvance;
		eloAvailable = listing.some((i) => i.score !== null);

		// A persisted `elo` preference is honored as-is; `effectiveMode` (used by
		// `initOrder`/`advance`) transparently walks it as `random` when this
		// context has no ELO scores, so the preference survives the visit.
		initOrder(idx);

		status = 'playing';
		startTimer();
	}

	function exit(): void {
		stop();
		items = [];
		current = 0;
		shuffleOrder = null;
		shufflePos = 0;
		ahead = [];
		history = [];
		historyPos = 0;
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
		if (items.length) initOrder(current);
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
		// The image shown's place in the listing walked, and the listing's size.
		get position() { return current; },
		get total() { return items.length; },
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
		upcoming,
		recent,
		back,
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
