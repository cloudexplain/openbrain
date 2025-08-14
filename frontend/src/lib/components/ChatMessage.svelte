<script lang="ts">
	import { marked } from 'marked';
	import { onMount } from 'svelte';

	export let message: {
		id: string;
		content: string;
		role: 'user' | 'assistant';
		timestamp: Date;
	};

	let parsedContent = '';

	// Configure marked options
	marked.setOptions({
		breaks: true, // Enable line breaks
		gfm: true, // Enable GitHub Flavored Markdown
	});

	$: {
		if (message.role === 'assistant') {
			// Parse markdown for assistant messages
			parsedContent = marked.parse(message.content) as string;
		} else {
			// For user messages, just escape HTML and preserve line breaks
			parsedContent = message.content
				.replace(/&/g, '&amp;')
				.replace(/</g, '&lt;')
				.replace(/>/g, '&gt;')
				.replace(/\n/g, '<br>');
		}
	}

	function copyToClipboard() {
		navigator.clipboard.writeText(message.content).catch(err => {
			console.error('Failed to copy text: ', err);
		});
	}
</script>

<div class="group px-6 py-8 transition-colors duration-200 hover:bg-gray-50/30">
	<div class="max-w-3xl mx-auto">
		<div class="flex gap-6">
			<!-- Avatar -->
			<div class="flex-shrink-0 mt-1">
				{#if message.role === 'user'}
					<div class="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-sm">
						<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
						</svg>
					</div>
				{:else}
					<div class="w-7 h-7 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center shadow-sm">
						<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
						</svg>
					</div>
				{/if}
			</div>
			
			<!-- Message Content -->
			<div class="flex-1 min-w-0">
				<!-- Role Label -->
				<div class="flex items-center gap-2 mb-3">
					<span class="text-sm font-medium text-gray-900">
						{message.role === 'user' ? 'You' : 'Assistant'}
					</span>
				</div>
				
				<!-- Message Text -->
				<div class="prose prose-sm prose-gray max-w-none text-gray-800 leading-relaxed 
							prose-headings:text-gray-900 prose-headings:font-semibold
							prose-a:text-blue-600 hover:prose-a:text-blue-800 prose-a:no-underline hover:prose-a:underline
							prose-code:text-gray-900 prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-medium
							prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200 prose-pre:rounded-lg prose-pre:p-4 prose-pre:overflow-x-auto
							prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-50/50 prose-blockquote:p-4 prose-blockquote:rounded-r-lg
							prose-ul:list-disc prose-ol:list-decimal prose-li:my-1
							prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:p-2 prose-th:bg-gray-50 prose-td:border prose-td:border-gray-300 prose-td:p-2">
					{@html parsedContent}
				</div>
				
				<!-- Action Buttons (for assistant messages) -->
				{#if message.role === 'assistant'}
					<div class="flex items-center gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
						<button on:click={copyToClipboard} class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors duration-150">
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
							</svg>
							Copy
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
