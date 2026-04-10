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

	function setSort(field: SortField) {
		if (field === sort) {
			const newDir = dir === 'asc' ? 'desc' : 'asc';
			onchange?.(field, newDir);
		} else {
			onchange?.(field, 'asc');
		}
	}
</script>

<div class="sort-controls">
	{#each fields as field}
		<button
			class:active={sort === field.value}
			onclick={() => setSort(field.value)}
		>
			{field.label}
			{#if sort === field.value}
				<span class="arrow">{dir === 'asc' ? '↑' : '↓'}</span>
			{/if}
		</button>
	{/each}
</div>

<style>
	.sort-controls {
		display: flex;
		gap: 4px;
		padding: 8px;
	}

	button {
		padding: 4px 10px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
		font-size: 0.85rem;
	}

	button:hover {
		background: #3a3a3a;
	}

	button.active {
		background: #3a5a8a;
		border-color: #6ea8fe;
		color: #fff;
	}

	.arrow {
		margin-left: 2px;
	}
</style>
