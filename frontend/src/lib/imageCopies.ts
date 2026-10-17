import type { ImageCopy } from './types';

/** The copy's full path on the server. */
export function copyPath(copy: ImageCopy): string {
	return `${copy.source_path.replace(/\/+$/, '')}/${copy.relative_path}`;
}

/** Folders of the sources holding a copy that Thalimage may not change. */
export function readOnlySources(copies: ImageCopy[]): string[] {
	return [...new Set(copies.filter((c) => !c.writable).map((c) => c.source_path))];
}

/** The copy once renamed to the image's hash: same folder, extension as found. */
export function hashNamed(copy: ImageCopy, hash: string): ImageCopy {
	const slash = copy.relative_path.lastIndexOf('/');
	const folder = copy.relative_path.slice(0, slash + 1);
	const name = copy.relative_path.slice(slash + 1);
	const dot = name.lastIndexOf('.');
	const extension = dot > 0 ? name.slice(dot) : '';
	return { ...copy, relative_path: `${folder}${hash}${extension}` };
}
