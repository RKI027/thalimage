<script lang="ts">
	import type { SortField, SortDirection } from '$lib/types';

	let {
		sort = 'name',
		dir = 'asc',
		allowElo = false,
		onchange
	}: {
		sort?: SortField;
		dir?: SortDirection;
		allowElo?: boolean;
		onchange?: (sort: SortField, dir: SortDirection) => void;
	} = $props();

	const baseFields: { value: SortField; label: string }[] = [
		{ value: 'name', label: 'Name' },
		{ value: 'date_modified', label: 'Modified' },
		{ value: 'date_created', label: 'Created' },
		{ value: 'size', label: 'Size' },
		{ value: 'aspect_ratio', label: 'Aspect' }
	];

	// ELO ranking only makes sense within a collection (not "All Images").
	const fields = $derived(
		allowElo ? [...baseFields, { value: 'elo' as SortField, label: 'ELO' }] : baseFields
	);

	function onFieldChange(e: Event) {
		const newSort = (e.target as HTMLSelectElement).value as SortField;
		// Default ELO to descending so the best-ranked images come first.
		onchange?.(newSort, newSort === 'elo' ? 'desc' : dir);
	}

	function toggleDir() {
		onchange?.(sort, dir === 'asc' ? 'desc' : 'asc');
	}
</script>

<div class="sort-controls">
	<select class="control" value={sort} onchange={onFieldChange}>
		{#each fields as field}
			<option value={field.value}>{field.label}</option>
		{/each}
	</select>
	<button class="control dir-btn" onclick={toggleDir} title={dir === 'asc' ? 'Ascending' : 'Descending'}>
		{dir === 'asc' ? '↑' : '↓'}
	</button>
</div>

<style>
	.dir-btn {
		justify-content: center;
		padding: 0;
		width: var(--control-min-height);
	}

	.sort-controls {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 8px;
	}

	@media (max-width: 768px) {
		.sort-controls {
			padding: 4px;
		}

	}
</style>