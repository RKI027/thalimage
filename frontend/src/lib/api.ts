import type {
	ImagePage,
	ImageDetail,
	Source,
	Collection,
	ScanProgress,
	EloPair,
	EloRanking,
	SortField,
	SortDirection
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

export function listImages(params: {
	cursor?: string | null;
	limit?: number;
	sort?: SortField;
	dir?: SortDirection;
	source_id?: number;
	collection_id?: number;
} = {}): Promise<ImagePage> {
	const q = new URLSearchParams();
	if (params.cursor) q.set('cursor', params.cursor);
	if (params.limit) q.set('limit', String(params.limit));
	if (params.sort) q.set('sort', params.sort);
	if (params.dir) q.set('dir', params.dir);
	if (params.source_id) q.set('source_id', String(params.source_id));
	if (params.collection_id) q.set('collection_id', String(params.collection_id));
	return fetchJSON(`${BASE}/images?${q}`);
}

export function getImage(hash: string): Promise<ImageDetail> {
	return fetchJSON(`${BASE}/images/${hash}`);
}

export function imageFileUrl(hash: string): string {
	return `${BASE}/images/${hash}/file`;
}

export function thumbUrl(hash: string): string {
	return `${BASE}/images/${hash}/thumb`;
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
	updates: { name?: string; sort_by?: string; sort_dir?: string }
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

export function addImagesToCollection(
	collectionId: number,
	hashes: string[]
): Promise<{ added: number }> {
	return fetchJSON(`${BASE}/collections/${collectionId}/images`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ hashes })
	});
}

export function removeImagesFromCollection(
	collectionId: number,
	hashes: string[]
): Promise<{ removed: number }> {
	return fetchJSON(`${BASE}/collections/${collectionId}/images`, {
		method: 'DELETE',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ hashes })
	});
}

// ELO Voting

export function getEloPair(collectionId: number): Promise<EloPair> {
	return fetchJSON(`${BASE}/collections/${collectionId}/elo/pair`);
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
