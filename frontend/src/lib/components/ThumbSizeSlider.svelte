<script lang="ts">
	let { size = $bindable(200) }: { size: number } = $props();
</script>

<label class="thumb-slider">
	<input type="range" min={100} max={400} step={25} bind:value={size} />
</label>

<style>
	.thumb-slider {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	input[type='range'] {
		width: 100px;
		accent-color: #6ea8fe;
		cursor: pointer;
	}
</style>
