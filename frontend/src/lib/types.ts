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

/** One image of a listing, as a slideshow walks it. `score` is its ELO
 * score in the collection browsed (null outside a collection). */
export interface SequenceItem {
	content_hash: string;
	filename: string;
	score: number | null;
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
	/** The top or bottom `elo_percent` of the collection's ELO ranking. */
	elo_end?: EloEnd;
	elo_percent?: number;
}

export type EloEnd = 'top' | 'bottom';

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

/** An image's line in a collection's ranking; equal scores share a rank. */
export interface EloRanked {
	image: ImageSummary;
	rank: number;
	score: number;
	matches: number;
	wins: number;
	losses: number;
}

/** An image voting can draw; `score` and `rank` are null until voted on. */
export interface CoveredImage {
	content_hash: string;
	filename: string;
	/** Hidden while NSFW images are hidden. */
	nsfw: boolean;
	matches: number;
	score: number | null;
	rank: number | null;
}

export interface Meeting {
	winner: string;
	loser: string;
	count: number;
}

/** A collection's voting statistics; `top` is the head of the ranking
 * among `images`, with `head_to_head` the results among those. */
export interface EloStats {
	images: CoveredImage[];
	pairs: { met: number; possible: number; repeated: number; most_meetings: number };
	top: CoveredImage[];
	head_to_head: Meeting[];
}

/** `total` counts the lines the listing can show; `ranked` every ranked image. */
export interface EloRankingPage {
	items: EloRanked[];
	total: number;
	ranked: number;
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

/** An image's place in one collection's ELO ranking. */
export interface EloStanding {
	collection_id: number;
	collection_name: string;
	score: number;
	/** 1 + the live scored images with a higher score; `ranked` counts them all. */
	rank: number;
	ranked: number;
	matches: number;
	wins: number;
	losses: number;
}
