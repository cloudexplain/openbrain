<script lang="ts">
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	
	export let message: string = '';
	export let type: 'success' | 'error' | 'info' = 'success';
	export let duration: number = 3000;
	export let onClose: () => void = () => {};
	
	let visible = true;
	
	onMount(() => {
		const timer = setTimeout(() => {
			visible = false;
			setTimeout(() => {
				onClose();
			}, 300); // Wait for exit animation
		}, duration);
		
		return () => clearTimeout(timer);
	});
	
	const typeStyles = {
		success: 'bg-green-500 text-white',
		error: 'bg-red-500 text-white',
		info: 'bg-blue-500 text-white'
	};
	
	const icons = {
		success: '✅',
		error: '❌',
		info: 'ℹ️'
	};
</script>

{#if visible}
	<div
		class="fixed top-4 right-4 z-[100] max-w-md"
		transition:fly={{ y: -20, duration: 300 }}
	>
		<div class="rounded-lg shadow-lg px-4 py-3 flex items-center gap-3 {typeStyles[type]}">
			<div class="text-lg">
				{icons[type]}
			</div>
			<div class="flex-1 text-sm font-medium">
				{message}
			</div>
			<button
				on:click={() => {
					visible = false;
					setTimeout(() => onClose(), 300);
				}}
				class="opacity-70 hover:opacity-100 transition-opacity"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</div>
	</div>
{/if}