<script lang="ts">
	import { withEloCut } from '$lib/eloCut';
	import { withFilters } from '$lib/filters';
	import type { EloEnd, FilterState } from '$lib/types';

	let {
		filters = {},
		allowElo = false,
		onchange
	}: {
		filters?: FilterState;
		/** Offer the ELO cut: only a collection has a ranking. */
		allowElo?: boolean;
		onchange?: (filters: FilterState) => void;
	} = $props();

	// The end chosen before a percentage is typed in; the filters only hold
	// one together with its percentage.
	let pendingEnd: EloEnd = $state('top');
	const eloEnd = $derived(filters.elo_end ?? pendingEnd);

	/** Applies the cut and returns the percentage kept (clamped, or none). */
	function setEloCut(end: EloEnd, raw: string): number | undefined {
		pendingEnd = end;
		const next = withEloCut(filters, end, raw === '' ? undefined : Number(raw));
		if (next.elo_percent !== filters.elo_percent || next.elo_end !== filters.elo_end) onchange?.(next);
		return next.elo_percent;
	}

	function update(patch: Partial<FilterState>) {
		onchange?.(withFilters(filters, patch));
	}
</script>

<div class="filter-bar">
	<div class="filter-group">
		<label for="filter-date-from">From</label>
		<input
			id="filter-date-from"
			class="control"
			type="date"
			value={filters.date_from?.slice(0, 10) ?? ''}
			onchange={(e) => {
				const v = (e.target as HTMLInputElement).value;
				update({ date_from: /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined });
			}}
		/>
	</div>

	<div class="filter-group">
		<label for="filter-date-to">To</label>
		<input
			id="filter-date-to"
			class="control"
			type="date"
			value={filters.date_to?.slice(0, 10) ?? ''}
			onchange={(e) => {
				const v = (e.target as HTMLInputElement).value;
				update({ date_to: /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : undefined });
			}}
		/>
	</div>

	<div class="filter-group">
		<label for="filter-aspect">Shape</label>
		<select
			id="filter-aspect"
			class="control"
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
			class="control"
			value={filters.media_type ?? ''}
			onchange={(e) => update({ media_type: (e.target as HTMLSelectElement).value || undefined })}
		>
			<option value="">All</option>
			<option value="image">Images</option>
			<option value="video">Videos</option>
		</select>
	</div>

	<div class="filter-group">
		<label for="filter-tags">Tags</label>
		<input
			id="filter-tags"
			class="control"
			type="text"
			placeholder="tag1, tag2"
			value={filters.tags?.join(', ') ?? ''}
			onchange={(e) => {
				const raw = (e.target as HTMLInputElement).value;
				const parsed = raw
					.split(',')
					.map((t) => t.trim())
					.filter(Boolean);
				update({ tags: parsed.length > 0 ? parsed : undefined });
			}}
		/>
	</div>

	<div class="filter-group">
		<label for="filter-archived">Archived</label>
		<select
			id="filter-archived"
			class="control"
			title="Archived images are left out of browsing; list them here to find and unarchive them"
			value={filters.archived ? 'only' : ''}
			onchange={(e) => update({ archived: (e.target as HTMLSelectElement).value === 'only' || undefined })}
		>
			<option value="">Hidden</option>
			<option value="only">Only</option>
		</select>
	</div>

	{#if allowElo}
		<div class="filter-group">
			<label for="filter-elo-end">ELO</label>
			<select
				id="filter-elo-end"
				class="control"
				value={eloEnd}
				onchange={(e) => setEloCut((e.target as HTMLSelectElement).value as EloEnd, String(filters.elo_percent ?? ''))}
			>
				<option value="top">Top</option>
				<option value="bottom">Bottom</option>
			</select>
			<input
				id="filter-elo-percent"
				class="control elo-percent"
				type="number"
				min="1"
				max="100"
				placeholder="all"
				aria-label="ELO share, in percent"
				value={filters.elo_percent ?? ''}
				onchange={(e) => {
					// Show the value kept, which the prop alone would not
					// refresh when clamping leaves the filters unchanged.
					const input = e.target as HTMLInputElement;
					input.value = String(setEloCut(eloEnd, input.value) ?? '');
				}}
			/>
			<span class="unit">%</span>
		</div>
	{/if}

	{#if Object.keys(filters).length > 0}
		<button class="control" onclick={() => onchange?.({})}>✕ Clear</button>
	{/if}
</div>

<style>
	.filter-bar {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 8px;
		padding: 4px;
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 4px;
		width: 100%;
	}

	label,
	.unit {
		font-size: 0.8rem;
		color: #888;
		white-space: nowrap;
	}

	.filter-group label {
		min-width: 60px;
	}

	.elo-percent {
		width: 4.5em;
	}
</style>
