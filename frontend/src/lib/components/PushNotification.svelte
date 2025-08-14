<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	
	export let message: string;
	export let type: 'success' | 'error' | 'info' | 'processing' = 'info';
	export let duration: number = 3000;
	export let onClose: () => void = () => {};
	
	onMount(() => {
		if (duration > 0) {
			const timer = setTimeout(() => {
				onClose();
			}, duration);
			
			return () => clearTimeout(timer);
		}
	});
	
	function getIcon() {
		switch (type) {
			case 'success':
				return '✓';
			case 'error':
				return '✕';
			case 'processing':
				return '⟳';
			default:
				return 'ℹ';
		}
	}
	
	function getColorClasses() {
		switch (type) {
			case 'success':
				return 'bg-green-500 text-white';
			case 'error':
				return 'bg-red-500 text-white';
			case 'processing':
				return 'bg-blue-500 text-white';
			default:
				return 'bg-gray-700 text-white';
		}
	}
</script>

<div
	class="fixed bottom-4 right-4 z-50"
	in:fly={{ y: 20, duration: 300 }}
	out:fade={{ duration: 200 }}
>
	<div class="flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg {getColorClasses()} min-w-[300px] max-w-md">
		<div class="flex-shrink-0">
			<div class="w-6 h-6 flex items-center justify-center rounded-full bg-white/20 text-sm font-bold {type === 'processing' ? 'animate-spin' : ''}">
				{getIcon()}
			</div>
		</div>
		<div class="flex-1 text-sm font-medium">
			{message}
		</div>
		{#if duration === 0}
			<button
				on:click={onClose}
				class="flex-shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		{/if}
	</div>
</div>
