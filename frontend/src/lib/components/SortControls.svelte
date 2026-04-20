<script lang="ts">
	import type { SortField, SortDirection } from '$lib/types';

	let {
		sort = 'name',
		dir = 'asc',
		onchange
	}: {
		sort?: SortField;
		dir?: SortDirection;
		onchange?: (sort: SortField, dir: SortDirection) => void;
	} = $props();

	const fields: { value: SortField; label: string }[] = [
		{ value: 'name', label: 'Name' },
		{ value: 'date_modified', label: 'Modified' },
		{ value: 'date_created', label: 'Created' },
		{ value: 'size', label: 'Size' },
		{ value: 'aspect_ratio', label: 'Aspect' }
	];

	function onFieldChange(e: Event) {
		onchange?.((e.target as HTMLSelectElement).value as SortField, dir);
	}

	function toggleDir() {
		onchange?.(sort, dir === 'asc' ? 'desc' : 'asc');
	}
</script>

<div class="sort-controls">
	<select value={sort} onchange={onFieldChange}>
		{#each fields as field}
			<option value={field.value}>{field.label}</option>
		{/each}
	</select>
	<button class="dir-btn" onclick={toggleDir} title={dir === 'asc' ? 'Ascending' : 'Descending'}>
		{dir === 'asc' ? '↑' : '↓'}
	</button>
</div>

<style>
	.sort-controls {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 8px;
	}

	select {
		padding: 4px 8px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
		font-size: 0.85rem;
	}

	select:focus {
		outline: none;
		border-color: #6ea8fe;
	}

	.dir-btn {
		padding: 4px 8px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
		font-size: 0.85rem;
		line-height: 1;
	}

	.dir-btn:hover {
		background: #3a3a3a;
	}

	@media (max-width: 768px) {
		.sort-controls {
			padding: 4px;
		}

		select,
		.dir-btn {
			padding: 10px 12px;
		}
	}
</style>