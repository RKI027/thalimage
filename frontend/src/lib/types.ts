export interface ImageSummary {
	content_hash: string;
	filename: string;
	source_id: number;
	relative_path: string;
	width: number;
	height: number;
	aspect_ratio: number;
	format: string;
	thumb_generated: boolean;
	archived: boolean;
	nsfw: boolean;
}

export interface Tag {
	id: number;
	name: string;
	created_at: string;
}

export interface UserSettings {
	show_nsfw: boolean;
}

export interface BackupConfig {
	enabled: boolean;
	/** Local time of day, HH:MM, in the server's time zone. */
	time: string;
	keep: number;
}

export interface BackupRecord {
	at: string;
	file: string | null;
	size: number | null;
	error: string | null;
}

export interface BackupStatus {
	config: BackupConfig;
	last: BackupRecord | null;
	running: boolean;
}

export interface ImageDetail extends ImageSummary {
	file_size: number;
	file_modified: string;
	file_created: string | null;
	ai_tool: string | null;
	prompt: string | null;
	negative_prompt: string | null;
	raw_params: string | null;
	exif_data: string | null;
	png_text: string | null;
}

export interface ImagePage {
	items: ImageSummary[];
	next_cursor: string | null;
	total_count: number;
}

export interface Neighbors {
	before: ImageSummary[];
	after: ImageSummary[];
	position: number;
	total_count: number;
}

export interface Source {
	id: number;
	path: string;
	label: string | null;
	recursive: boolean;
	enabled: boolean;
	/** Thalimage may change files in this source (delete, rename, move). */
	writable: boolean;
	created_at: string;
	last_scan: string | null;
}

export interface Collection {
	id: number;
	name: string;
	parent_id: number | null;
	type: string;
	source_id: number | null;
	sort_by: string;
	sort_dir: string;
	nsfw: boolean;
	created_at: string;
	updated_at: string;
	/** Images browsing the collection shows. */
	image_count: number;
	/** Archived images in the collection, not shown when browsing. */
	archived_count: number;
}

/** What a source holds: its files against its images, and why they differ. */
export interface SourceSummary {
	/** Files indexed in the source. */
	files: number;
	/** Images browsing the source shows. */
	images: number;
	/** Files in the source with the same content: one image each, with each file's sidecars. */
	duplicates: {
		content_hash: string;
		paths: string[];
		sidecars: Record<string, { relative_path: string; digest: string }[]>;
	}[];
	archived: { content_hash: string; relative_path: string }[];
	/** What the latest scan could not index; a folder ends with a separator. */
	failures: { relative_path: string; reason: string }[];
}

export interface ScanProgress {
	source_id: number;
	phase: string;
	current: number;
	total: number;
	added: number;
	skipped: number;
	errors: number;
	message: string;
}

export interface FilterState {
	date_from?: string;
	date_to?: string;
	aspect_ratio?: string;
	media_type?: string;
	tags?: string[];
}

export type SortField = 'name' | 'date_modified' | 'date_created' | 'size' | 'aspect_ratio' | 'elo';
export type SortDirection = 'asc' | 'desc';
export type MetadataMode = 'hidden' | 'compact' | 'full';
export type SlideshowStatus = 'idle' | 'playing' | 'paused';
export type SlideshowMode = 'sequential' | 'random' | 'elo';
export type OverlayMode = 'none' | 'minimal' | 'full';

export interface EloPair {
	left: ImageSummary;
	right: ImageSummary;
}

export interface EloRanking {
	content_hash: string;
	filename: string;
	score: number;
	matches: number;
}

export interface DocSummary {
	slug: string;
	title: string;
}

export interface DocPage {
	slug: string;
	title: string;
	markdown: string;
}

export interface VersionInfo {
	version: string;
	commit: string | null;
}

/** One file holding an image's content. */
export interface ImageCopy {
	source_id: number;
	source_path: string;
	relative_path: string;
	writable: boolean;
	/** Sidecar files next to it, relative to the source. */
	sidecars: string[];
}
