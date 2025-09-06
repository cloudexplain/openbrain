<script lang="ts">
	import { authStore } from "$lib/stores/auth";

	function handleSuggestedPrompt(prompt: string) {
		// This will be handled by creating a new chat
		console.log("Suggested prompt:", prompt);
		// For now, just log it - the layout will handle new chat creation
	}
</script>

<!-- Landing Page -->
<div class="flex flex-col h-full bg-white overflow-hidden relative">
	<!-- Header -->
	{#if $authStore.user}
		<div class="flex justify-end px-6 py-3 border-b border-gray-100 bg-gray-50/50">
			<div class="flex items-center gap-2 text-sm text-gray-600">
				<span>Welcome, {$authStore.user.username}</span>
			</div>
		</div>
	{/if}

	<!-- Welcome Content -->
	<div class="flex-1 flex items-center justify-center p-8">
		<div class="text-center max-w-2xl">
			<div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-blue-500/25">
				<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
				</svg>
			</div>
			<h2 class="text-2xl font-bold text-gray-900 mb-3">Welcome to SecondBrain</h2>
			<p class="text-gray-600 mb-6 leading-relaxed">
				Your intelligent assistant that learns with you, curates your knowledge and helps you make sense of the world.
			</p>
			<p class="text-gray-500 mb-8">
				Start a new chat to begin your conversation, or explore your knowledge base and tags using the sidebar.
			</p>

			<!-- Action Cards -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
					<div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center mx-auto mb-4">
						<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
						</svg>
					</div>
					<h3 class="font-semibold text-gray-900 mb-2">Start Chatting</h3>
					<p class="text-sm text-gray-600">Click "New Chat" in the sidebar to begin a conversation with your AI assistant.</p>
				</div>

				<div class="p-6 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border border-green-200">
					<div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center mx-auto mb-4">
						<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
					</div>
					<h3 class="font-semibold text-gray-900 mb-2">Browse Knowledge</h3>
					<p class="text-sm text-gray-600">Explore your uploaded documents and saved conversations in the knowledge base.</p>
				</div>

				<div class="p-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border border-purple-200">
					<div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center mx-auto mb-4">
						<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
						</svg>
					</div>
					<h3 class="font-semibold text-gray-900 mb-2">Organize Tags</h3>
					<p class="text-sm text-gray-600">Manage and organize your content with tags for better discoverability.</p>
				</div>
			</div>
		</div>
	</div>
</div>