<script lang="ts">
	import { onMount } from 'svelte';
	import { getBackupStatus, patchBackupConfig, runBackupNow } from '$lib/api';
	import { describeBackup } from '$lib/format';
	import type { BackupConfig, BackupStatus } from '$lib/types';

	let status = $state<BackupStatus | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	async function load() {
		try {
			status = await getBackupStatus();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load backup settings';
		}
	}

	async function update(patch: Partial<BackupConfig>) {
		error = null;
		try {
			status = await patchBackupConfig(patch);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save backup settings';
			await load();
		}
	}

	async function backUpNow() {
		error = null;
		running = true;
		try {
			const last = await runBackupNow();
			if (status) status = { ...status, last };
		} catch (e) {
			error = e instanceof Error ? e.message : 'Backup failed';
		} finally {
			running = false;
		}
	}

	onMount(load);
</script>

<section class="backup-section">
	<h3>Database backup</h3>
	<p class="description">
		A daily copy of the database goes to <code>db_backups/</code> in the data folder.
		The time is the server's local time.
	</p>
	{#if status}
		<div class="pref-row">
			<label for="backup-enabled">Back up daily</label>
			<input
				id="backup-enabled"
				type="checkbox"
				checked={status.config.enabled}
				onchange={(e) => update({ enabled: e.currentTarget.checked })}
			/>
		</div>
		<div class="pref-row">
			<label for="backup-time">At</label>
			<input
				id="backup-time"
				type="time"
				class="control time-input"
				value={status.config.time}
				disabled={!status.config.enabled}
				onchange={(e) => e.currentTarget.value && update({ time: e.currentTarget.value })}
			/>
		</div>
		<div class="pref-row">
			<label for="backup-keep">Copies to keep</label>
			<input
				id="backup-keep"
				type="number"
				min="1"
				class="control keep-input"
				value={status.config.keep}
				onchange={(e) => {
					const keep = e.currentTarget.valueAsNumber;
					if (Number.isInteger(keep) && keep >= 1) update({ keep });
				}}
			/>
		</div>
		<div class="last-row">
			<span class="last" class:failed={status.last?.error}>
				Last backup: {describeBackup(status.last)}
			</span>
			<button
				class="control control-primary"
				disabled={running || status.running}
				onclick={backUpNow}
			>
				{running ? 'Backing up…' : 'Back up now'}
			</button>
		</div>
	{/if}
	{#if error}
		<p class="error">{error}</p>
	{/if}
</section>

<style>
	.backup-section {
		margin-bottom: 32px;
	}

	h3 {
		margin: 0 0 12px;
		font-size: 1rem;
		color: #ccc;
	}

	.description {
		color: #888;
		margin: 0 0 12px;
		font-size: 0.9rem;
	}

	.pref-row,
	.last-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 0;
		border-bottom: 1px solid #2a2a2a;
		font-size: 0.9rem;
		color: #ccc;
	}

	.pref-row label {
		flex: 1;
		cursor: pointer;
	}

	.pref-row input[type='checkbox'] {
		width: 16px;
		height: 16px;
		cursor: pointer;
		padding: 0;
		border: none;
		background: none;
		flex: none;
	}

	.time-input,
	.keep-input {
		flex: none;
		width: 7em;
	}

	.last {
		flex: 1;
		min-width: 0;
		color: #888;
		font-size: 0.85rem;
		/* Backup file names have no spaces to break at. */
		overflow-wrap: anywhere;
	}

	.last.failed,
	.error {
		color: #e0a458;
	}

	.error {
		margin: 8px 0 0;
		font-size: 0.85rem;
	}
</style>
