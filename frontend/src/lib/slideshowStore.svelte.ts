import type { ImageSummary, MetadataMode, OverlayMode, SlideshowStatus } from './types';

export interface SlideshowConfig {
	interval: number;
	shuffle: boolean;
}

function readLocalStorage<T>(key: string, fallback: T): T {
	try {
		const raw = localStorage.getItem(key);
		if (raw === null) return fallback;
		return JSON.parse(raw) as T;
	} catch {
		return fallback;
	}
}

function writeLocalStorage(key: string, value: unknown): void {
	try {
		localStorage.setItem(key, JSON.stringify(value));
	} catch {
		// ignore storage errors
	}
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
		interval: readLocalStorage('slideshow:interval', 5000),
		shuffle: readLocalStorage('slideshow:shuffle', false)
	});
	let metadataMode = $state<MetadataMode>(
		readLocalStorage('viewer:metadataMode', 'full' as MetadataMode)
	);
	let overlayMode = $state<OverlayMode>(
		readLocalStorage('slideshow:overlayMode', 'minimal' as OverlayMode)
	);

	// Internal runtime state (not reactive state — just bookkeeping)
	let neighbors: ImageSummary[] = [];
	let currentIndexRef = 0;
	let shuffleOrder: number[] | null = null;
	let shufflePos = 0;
	let timerId: ReturnType<typeof setInterval> | null = null;
	let onAdvanceCb: ((hash: string) => void) | null = null;

	function advance() {
		if (!neighbors.length) return;

		let nextIndex: number;
		if (config.shuffle && shuffleOrder) {
			shufflePos = (shufflePos + 1) % shuffleOrder.length;
			nextIndex = shuffleOrder[shufflePos];
		} else {
			nextIndex = currentIndexRef + 1;
			if (nextIndex >= neighbors.length) {
				// Stop at the end in sequential mode
				stop();
				return;
			}
			currentIndexRef = nextIndex;
		}

		onAdvanceCb?.(neighbors[nextIndex].content_hash);
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

	function enter(
		nbrs: ImageSummary[],
		idx: number,
		onAdvance: (hash: string) => void
	): void {
		neighbors = nbrs;
		currentIndexRef = idx;
		onAdvanceCb = onAdvance;

		if (config.shuffle) {
			shuffleOrder = fisherYates(neighbors.length, idx);
			shufflePos = 0;
		} else {
			shuffleOrder = null;
		}

		status = 'playing';
		startTimer();
	}

	function exit(): void {
		stop();
		neighbors = [];
		currentIndexRef = 0;
		shuffleOrder = null;
		shufflePos = 0;
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

	// Called by the page when the user navigates manually during slideshow
	function updateCurrentIndex(idx: number): void {
		currentIndexRef = idx;
		if (config.shuffle && shuffleOrder) {
			// Point shuffle position to the new index if it's in the order
			const pos = shuffleOrder.indexOf(idx);
			if (pos >= 0) shufflePos = pos;
		}
	}

	function setInterval_(ms: number): void {
		config = { ...config, interval: ms };
		writeLocalStorage('slideshow:interval', ms);
		if (status === 'playing') startTimer();
	}

	function toggleShuffle(): void {
		const next = !config.shuffle;
		config = { ...config, shuffle: next };
		writeLocalStorage('slideshow:shuffle', next);
		if (next && neighbors.length) {
			shuffleOrder = fisherYates(neighbors.length, currentIndexRef);
			shufflePos = 0;
		} else {
			shuffleOrder = null;
		}
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
		writeLocalStorage('viewer:metadataMode', mode);
	}

	function setOverlayMode(mode: OverlayMode): void {
		overlayMode = mode;
		writeLocalStorage('slideshow:overlayMode', mode);
	}

	return {
		get status() { return status; },
		get isFullscreen() { return isFullscreen; },
		get pendingStart() { return pendingStart; },
		get config() { return config; },
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
		updateCurrentIndex,
		setInterval: setInterval_,
		toggleShuffle,
		setIsFullscreen,
		toggleFullscreen,
		setMetadataMode,
		setOverlayMode
	};
}

export const slideshowStore = createSlideshowStore();
