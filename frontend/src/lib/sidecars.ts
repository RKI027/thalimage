import type { SidecarContent } from './types';

/** Sidecars that say the same thing, shown once under all their names. */
export interface DistinctSidecar {
	names: string[];
	size: number;
	text: string | null;
}

/** Merges sidecars with identical text; one without text stays on its own. */
export function distinctSidecars(sidecars: SidecarContent[]): DistinctSidecar[] {
	const distinct: DistinctSidecar[] = [];
	for (const s of sidecars) {
		const same = s.text !== null && distinct.find((d) => d.text === s.text);
		if (same) same.names.push(s.relative_path);
		else distinct.push({ names: [s.relative_path], size: s.size, text: s.text });
	}
	return distinct;
}
