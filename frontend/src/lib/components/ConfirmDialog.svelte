<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * A modal asking to confirm an action. Cancel has the focus, so Enter or
	 * Escape never confirms by accident; `danger` styles the confirm button
	 * for actions that cannot be undone. With `canConfirm` false the dialog
	 * only explains why the action is not possible.
	 */
	let {
		open,
		title,
		confirmLabel,
		danger = false,
		canConfirm = true,
		onconfirm,
		oncancel,
		children
	}: {
		open: boolean;
		title: string;
		confirmLabel: string;
		danger?: boolean;
		canConfirm?: boolean;
		onconfirm: () => void;
		oncancel: () => void;
		children: Snippet;
	} = $props();

	let dialog: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});
</script>

<dialog bind:this={dialog} oncancel={(e) => (e.preventDefault(), oncancel())} aria-labelledby="confirm-title">
	<h3 id="confirm-title">{title}</h3>
	<div class="body">{@render children()}</div>
	<div class="actions">
		<!-- svelte-ignore a11y_autofocus -->
		<button class="control" autofocus onclick={oncancel}>Cancel</button>
		{#if canConfirm}
			<button class="control {danger ? 'control-danger' : 'control-primary'}" onclick={onconfirm}>
				{confirmLabel}
			</button>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		max-width: min(560px, calc(100vw - 32px));
		padding: 20px;
		border: 1px solid #444;
		border-radius: 6px;
		background: #1e1e1e;
		color: #ddd;
	}

	dialog::backdrop {
		background: rgba(0, 0, 0, 0.6);
	}

	h3 {
		margin: 0 0 12px;
	}

	.body {
		font-size: 0.9rem;
		max-height: 50vh;
		overflow-y: auto;
		overflow-wrap: anywhere;
	}

	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 16px;
	}
</style>
