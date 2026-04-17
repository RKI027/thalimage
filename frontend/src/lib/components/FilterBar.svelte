<script lang="ts">
	import type { FilterState } from '$lib/types';

	let {
		filters = {},
		onchange
	}: {
		filters?: FilterState;
		onchange?: (filters: FilterState) => void;
	} = $props();

	function update(patch: Partial<FilterState>) {
		const next = { ...filters, ...patch };
		// Remove empty string values so they're treated as unset
		for (const k of Object.keys(next) as (keyof FilterState)[]) {
			if (next[k] === '') delete next[k];
		}
		onchange?.(next);
	}
</script>

<div class="filter-bar">
	<div class="filter-group">
		<label for="filter-date-from">From</label>
		<input
			id="filter-date-from"
			type="date"
			value={filters.date_from?.slice(0, 10) ?? ''}
			onchange={(e) => update({ date_from: (e.target as HTMLInputElement).value || undefined })}
		/>
	</div>

	<div class="filter-group">
		<label for="filter-date-to">To</label>
		<input
			id="filter-date-to"
			type="date"
			value={filters.date_to?.slice(0, 10) ?? ''}
			onchange={(e) => update({ date_to: (e.target as HTMLInputElement).value || undefined })}
		/>
	</div>

	<div class="filter-group">
		<label for="filter-aspect">Shape</label>
		<select
			id="filter-aspect"
			value={filters.aspect_ratio ?? ''}
			onchange={(e) => update({ aspect_ratio: (e.target as HTMLSelectElement).value || undefined })}
		>
			<option value="">All</option>
			<option value="portrait">Portrait</option>
			<option value="square">Square</option>
			<option value="landscape">Landscape</option>
			<option value="wide">Wide</option>
		</select>
	</div>

	<div class="filter-group">
		<label for="filter-media">Type</label>
		<select
			id="filter-media"
			value={filters.media_type ?? ''}
			onchange={(e) => update({ media_type: (e.target as HTMLSelectElement).value || undefined })}
		>
			<option value="">All</option>
			<option value="image">Images</option>
			<option value="video">Videos</option>
		</select>
	</div>

	{#if Object.keys(filters).length > 0}
		<button class="clear-btn" onclick={() => onchange?.({})}>✕ Clear</button>
	{/if}
</div>

<style>
	.filter-bar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		padding: 4px 8px;
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	label {
		font-size: 0.8rem;
		color: #888;
		white-space: nowrap;
	}

	input[type='date'],
	select {
		padding: 3px 6px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		font-size: 0.85rem;
		cursor: pointer;
	}

	input[type='date']:focus,
	select:focus {
		outline: none;
		border-color: #6ea8fe;
	}

	.clear-btn {
		padding: 3px 8px;
		border: 1px solid #666;
		border-radius: 4px;
		background: #2a2a2a;
		color: #aaa;
		cursor: pointer;
		font-size: 0.8rem;
	}

	.clear-btn:hover {
		background: #3a3a3a;
		color: #ccc;
	}

	@media (max-width: 768px) {
		.filter-bar {
			flex-direction: column;
			align-items: flex-start;
			padding: 4px;
		}

		input[type='date'],
		select {
			padding: 8px 6px;
			min-height: 44px;
			width: 100%;
		}

		.filter-group {
			width: 100%;
		}

		.filter-group label {
			min-width: 60px;
		}

		.clear-btn {
			align-self: flex-end;
			min-height: 44px;
			padding: 8px 16px;
		}
	}
</style>
