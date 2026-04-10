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

export interface Source {
	id: number;
	path: string;
	label: string | null;
	recursive: boolean;
	enabled: boolean;
	created_at: string;
	last_scan: string | null;
}

export interface Collection {
	id: number;
	name: string;
	parent_id: number | null;
	sort_by: string;
	sort_dir: string;
	created_at: string;
	updated_at: string;
	image_count: number;
}

export interface ScanResult {
	scanned: number;
	added: number;
	skipped: number;
	errors: number;
}

export type SortField = 'name' | 'date_modified' | 'date_created' | 'size' | 'aspect_ratio';
export type SortDirection = 'asc' | 'desc';
export type MetadataMode = 'hidden' | 'compact' | 'full';
