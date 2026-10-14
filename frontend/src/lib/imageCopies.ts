import type { ImageCopy } from './types';

/** The copy's full path on the server. */
export function copyPath(copy: ImageCopy): string {
	return `${copy.source_path.replace(/\/+$/, '')}/${copy.relative_path}`;
}

/** Folders of the sources holding a copy that Thalimage may not change. */
export function readOnlySources(copies: ImageCopy[]): string[] {
	return [...new Set(copies.filter((c) => !c.writable).map((c) => c.source_path))];
}
