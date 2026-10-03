import type {
	ImagePage,
	ImageDetail,
	Source,
	Collection,
	Tag,
	UserSettings,
	ScanProgress,
	EloPair,
	EloRanking,
	FilterState,
	SortField,
	SortDirection,
	DocSummary,
	DocPage,
	Neighbors,
	VersionInfo
} from './types';

const BASE = '/api/v1';

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
	const resp = await fetch(url, init);
	if (!resp.ok) {
		throw new Error(`API error ${resp.status}: ${await resp.text()}`);
	}
	return resp.json();
}

// Images

/** What a listing is: its order, scope and filters (no paging). */
export interface ListingParams {
	sort?: SortField;
	dir?: SortDirection;
	source_id?: number;
	collection_id?: number;
	filters?: FilterState;
	show_nsfw?: boolean;
}

/** The query string the backend reads a listing from. */
export function listingQuery(params: ListingParams): URLSearchParams {
	const q = new URLSearchParams();
	if (params.sort) q.set('sort', params.sort);
	if (params.dir) q.set('dir', params.dir);
	if (params.source_id) q.set('source_id', String(params.source_id));
	if (params.collection_id) q.set('collection_id', String(params.collection_id));
	if (params.show_nsfw) q.set('show_nsfw', 'true');
	if (params.filters) {
		const f = params.filters;
		if (f.date_from) q.set('date_from', f.date_from);
		if (f.date_to) q.set('date_to', f.date_to);
		if (f.aspect_ratio) q.set('aspect_ratio_filter', f.aspect_ratio);
		if (f.media_type) q.set('media_type', f.media_type);
		if (f.tags) f.tags.forEach((t) => q.append('tags', t));
	}
	return q;
}

export function listImages(
	params: ListingParams & { cursor?: string | null; limit?: number } = {},
	init?: RequestInit
): Promise<ImagePage> {
	const q = listingQuery(params);
	if (params.cursor) q.set('cursor', params.cursor);
	if (params.limit) q.set('limit', String(params.limit));
	return fetchJSON(`${BASE}/images?${q}`, init);
}

/** Up to `window` images either side of `hash` in a listing, with its place in it. */
export function getNeighbors(
	hash: string,
	params: ListingParams & { window?: number } = {},
	init?: RequestInit
): Promise<Neighbors> {
	const q = listingQuery(params);
	if (params.window) q.set('window', String(params.window));
	return fetchJSON(`${BASE}/images/${hash}/neighbors?${q}`, init);
}

export function getImage(hash: string): Promise<ImageDetail> {
	return fetchJSON(`${BASE}/images/${hash}`);
}

export function archiveImage(hash: string, archived: boolean): Promise<ImageDetail> {
	return fetchJSON(`${BASE}/images/${hash}/archive`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ archived })
	});
}

export function imageFileUrl(hash: string): string {
	return `${BASE}/images/${hash}/file`;
}

export function thumbUrl(hash: string): string {
	return `${BASE}/images/${hash}/thumb`;
}

/** The largest preview the server makes (PREVIEW_SIZES in core/previews.py). */
const LARGEST_PREVIEW = 2560;

/**
 * Long edge, in device pixels, needed to fill this screen. The server snaps it
 * up to its nearest size bucket, so an exact value is not required. Capped at
 * the largest bucket: asking for more gets the same file under another URL.
 */
export function displaySize(): number {
	if (typeof window === 'undefined') return 1920;
	const dpr = Math.min(window.devicePixelRatio || 1, 2);
	const wanted = Math.round(Math.max(window.innerWidth, window.innerHeight) * dpr);
	return Math.min(wanted, LARGEST_PREVIEW);
}

/**
 * A display-sized WebP rather than the original. Originals average several
 * megabytes and are far larger than any screen needs, which is felt over wifi.
 */
export function previewUrl(hash: string, size: number = displaySize()): string {
	return `${BASE}/images/${hash}/preview?size=${size}`;
}

// Sources

export function listSources(): Promise<Source[]> {
	return fetchJSON(`${BASE}/sources`);
}

export function createSource(path: string, label?: string, recursive = true): Promise<Source> {
	return fetchJSON(`${BASE}/sources`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ path, label, recursive })
	});
}

export async function deleteSource(id: number): Promise<void> {
	const resp = await fetch(`${BASE}/sources/${id}`, { method: 'DELETE' });
	if (!resp.ok) throw new Error(`Delete failed: ${resp.status}`);
}

export async function triggerScan(sourceId: number): Promise<{ status: string }> {
	return fetchJSON(`${BASE}/sources/${sourceId}/scan`, { method: 'POST' });
}

export function subscribeScanProgress(
	sourceId: number,
	onProgress: (data: ScanProgress) => void
): () => void {
	const es = new EventSource(`${BASE}/sources/${sourceId}/scan/status`);
	es.addEventListener('status', (e) => {
		onProgress(JSON.parse(e.data));
	});
	es.onerror = () => { es.close(); };
	return () => es.close();
}

// Collections

export function listCollections(): Promise<Collection[]> {
	return fetchJSON(`${BASE}/collections`);
}

export function getCollection(id: number): Promise<Collection> {
	return fetchJSON(`${BASE}/collections/${id}`);
}

export function createCollection(name: string, parentId?: number): Promise<Collection> {
	return fetchJSON(`${BASE}/collections`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, parent_id: parentId })
	});
}

export function updateCollection(
	id: number,
	updates: { name?: string; sort_by?: string; sort_dir?: string; nsfw?: boolean }
): Promise<Collection> {
	return fetchJSON(`${BASE}/collections/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updates)
	});
}

export async function deleteCollection(id: number): Promise<void> {
	const resp = await fetch(`${BASE}/collections/${id}`, { method: 'DELETE' });
	if (!resp.ok) throw new Error(`Delete failed: ${resp.status}`);
}

// ELO Voting

export function getEloPair(collectionId: number, filters: FilterState = {}, showNsfw = false): Promise<EloPair> {
	const q = new URLSearchParams();
	if (filters.date_from) q.set('date_from', filters.date_from);
	if (filters.date_to) q.set('date_to', filters.date_to);
	if (filters.aspect_ratio) q.set('aspect_ratio_filter', filters.aspect_ratio);
	if (filters.media_type) q.set('media_type', filters.media_type);
	if (showNsfw) q.set('show_nsfw', 'true');
	const qs = q.toString();
	return fetchJSON(`${BASE}/collections/${collectionId}/elo/pair${qs ? '?' + qs : ''}`);
}

export function recordEloVote(
	collectionId: number,
	winnerHash: string,
	loserHash: string
): Promise<{ status: string }> {
	return fetchJSON(`${BASE}/collections/${collectionId}/elo/vote`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ winner_hash: winnerHash, loser_hash: loserHash })
	});
}

export function getEloRankings(collectionId: number, limit = 100): Promise<EloRanking[]> {
	return fetchJSON(`${BASE}/collections/${collectionId}/elo/rankings?limit=${limit}`);
}

// Tags

export function listTags(search?: string): Promise<Tag[]> {
	const q = search ? `?search=${encodeURIComponent(search)}` : '';
	return fetchJSON(`${BASE}/tags${q}`);
}

export function createTag(name: string): Promise<Tag> {
	return fetchJSON(`${BASE}/tags`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name })
	});
}

export function getImageTags(hash: string): Promise<Tag[]> {
	return fetchJSON(`${BASE}/images/${hash}/tags`);
}

export async function addImageTag(hash: string, tagId: number): Promise<void> {
	const resp = await fetch(`${BASE}/images/${hash}/tags`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ tag_id: tagId })
	});
	if (!resp.ok) throw new Error(`Add tag failed: ${resp.status}`);
}

export async function removeImageTag(hash: string, tagId: number): Promise<void> {
	const resp = await fetch(`${BASE}/images/${hash}/tags/${tagId}`, { method: 'DELETE' });
	if (!resp.ok) throw new Error(`Remove tag failed: ${resp.status}`);
}

// Settings

export function getSettings(): Promise<UserSettings> {
	return fetchJSON(`${BASE}/settings`);
}

export function patchSettings(patch: Partial<UserSettings>): Promise<UserSettings> {
	return fetchJSON(`${BASE}/settings`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(patch)
	});
}

// Documentation

export function listDocs(): Promise<DocSummary[]> {
	return fetchJSON(`${BASE}/docs`);
}

export function getDoc(slug: string): Promise<DocPage> {
	return fetchJSON(`${BASE}/docs/${slug}`);
}

export function getVersion(): Promise<VersionInfo> {
	return fetchJSON(`${BASE}/version`);
}
