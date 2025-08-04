<script lang="ts">
	export let type: 'typing' | 'loading' = 'typing';
</script>

{#if type === 'typing'}
	<div class="group px-6 py-8 transition-colors duration-200">
		<div class="max-w-3xl mx-auto">
			<div class="flex gap-6">
				<!-- Avatar -->
				<div class="flex-shrink-0 mt-1">
					<div class="w-7 h-7 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center shadow-sm">
						<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
						</svg>
					</div>
				</div>
				
				<!-- Message Content -->
				<div class="flex-1 min-w-0">
					<!-- Role Label -->
					<div class="flex items-center gap-2 mb-3">
						<span class="text-sm font-medium text-gray-900">Assistant</span>
					</div>
					
					<!-- Typing Animation -->
					<div class="flex items-center gap-2">
						<div class="flex gap-1">
							<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce-slow"></div>
							<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce-slow" style="animation-delay: 0.2s"></div>
							<div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce-slow" style="animation-delay: 0.4s"></div>
						</div>
						<span class="text-sm text-gray-500">Thinking...</span>
					</div>
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center p-6">
		<div class="animate-spin rounded-full h-6 w-6 border-2 border-orange-200 border-t-orange-500"></div>
		<span class="ml-3 text-sm text-gray-600">Loading...</span>
	</div>
{/if}

<style>
	@keyframes bounce-slow {
		0%, 80%, 100% {
			transform: translateY(0);
			opacity: 0.4;
		}
		40% {
			transform: translateY(-6px);
			opacity: 1;
		}
	}
	
	.animate-bounce-slow {
		animation: bounce-slow 1.4s ease-in-out infinite;
	}
</style>