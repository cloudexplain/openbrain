<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let disabled = false;
	export let placeholder = 'Send a message...';
	
	let message = '';
	let textarea: HTMLTextAreaElement;
	
	const dispatch = createEventDispatcher<{
		send: { content: string };
	}>();

	function autoResize() {
		if (textarea) {
			textarea.style.height = '24px';
			textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
		}
	}

	function handleSubmit() {
		if (message.trim() && !disabled) {
			dispatch('send', { content: message.trim() });
			message = '';
			setTimeout(autoResize, 0); // Delay to ensure DOM update
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSubmit();
		}
	}
</script>

<div class="border-t border-gray-200 bg-white">
	<div class="max-w-3xl mx-auto px-6 py-6">
		<div class="relative">
			<!-- Input Container -->
			<div class="relative flex items-end bg-white border border-gray-300 rounded-2xl shadow-sm hover:border-gray-400 focus-within:border-orange-500 focus-within:ring-2 focus-within:ring-orange-500/20 transition-all duration-200">
				<textarea
					bind:this={textarea}
					bind:value={message}
					on:input={autoResize}
					on:keydown={handleKeydown}
					{placeholder}
					{disabled}
					rows="1"
					class="flex-1 resize-none border-0 outline-0 bg-transparent px-4 py-3 text-[15px] leading-6 text-gray-900 placeholder-gray-500 focus:ring-0"
					style="min-height: 24px; max-height: 200px;"
				></textarea>
				
				<!-- Send Button -->
				<div class="flex-shrink-0 pr-3 pb-3">
					<button
						on:click={handleSubmit}
						disabled={!message.trim() || disabled}
						class="flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200 {
							message.trim() && !disabled 
								? 'bg-gray-900 hover:bg-gray-800 text-white shadow-sm' 
								: 'bg-gray-100 text-gray-400 cursor-not-allowed'
						}"
						title="Send message"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
						</svg>
					</button>
				</div>
			</div>
			
			<!-- Helper Text -->
			<div class="flex items-center justify-between mt-2 px-2">
				<div class="text-xs text-gray-500">
					Press Enter to send, Shift+Enter for new line
				</div>
				<div class="text-xs text-gray-400">
					{message.length}/2000
				</div>
			</div>
		</div>
	</div>
</div>