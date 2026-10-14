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
