/** Display formatting shared across pages. */
import type { BackupRecord } from './types';

export function formatSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** One line on the latest backup run: what it wrote, or why it failed. */
export function describeBackup(record: BackupRecord | null): string {
	if (record === null) return 'No backup yet';
	const when = new Date(record.at).toLocaleString();
	if (record.error !== null) return `Failed ${when}: ${record.error}`;
	return `${when} · ${record.file} · ${formatSize(record.size ?? 0)}`;
}
