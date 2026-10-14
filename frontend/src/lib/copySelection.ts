/** Choosing which copies of duplicated images to delete: every group keeps at least one. */

interface Group {
	paths: string[];
}

/** Whether `path` may be (or stay) selected: selecting it must leave a copy of its group unselected. */
export function canSelect(group: Group, selected: Set<string>, path: string): boolean {
	if (selected.has(path)) return true;
	return group.paths.some((p) => p !== path && !selected.has(p));
}

/** `selected` with `path` added or removed. */
export function toggled(selected: Set<string>, path: string): Set<string> {
	const next = new Set(selected);
	if (!next.delete(path)) next.add(path);
	return next;
}

/** Every copy but the first of each group: keep one, delete the rest. */
export function allButFirst(groups: Group[]): Set<string> {
	return new Set(groups.flatMap((g) => g.paths.slice(1)));
}

interface GroupWithSidecars extends Group {
	sidecars: Record<string, { relative_path: string; digest: string }[]>;
}

/**
 * Sidecars that deleting the selected copies would lose: those of a selected
 * copy whose content no kept copy of the same group has in a sidecar.
 */
export function unmatchedSidecars(groups: GroupWithSidecars[], selected: Set<string>): string[] {
	return groups.flatMap((g) => {
		const kept = new Set(
			g.paths.filter((p) => !selected.has(p)).flatMap((p) => (g.sidecars[p] ?? []).map((s) => s.digest))
		);
		return g.paths
			.filter((p) => selected.has(p))
			.flatMap((p) => g.sidecars[p] ?? [])
			.filter((s) => !kept.has(s.digest))
			.map((s) => s.relative_path);
	});
}
