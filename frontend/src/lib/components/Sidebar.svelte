<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let chats: Array<{
		id: string;
		title: string;
		created_at: string;
		updated_at: string;
		last_message?: string;
		message_count: number;
	}> = [];
	
	export let currentChatId: string | null = null;
	export let isMinimized: boolean = false;
	
	const dispatch = createEventDispatcher<{
		selectChat: { id: string };
		newChat: {};
		deleteChat: { id: string };
		toggleMinimize: {};
		toggleKnowledgeBase: {};
		toggleTags: {};
	}>();

	function selectChat(id: string) {
		console.log('[Sidebar] selectChat called with ID:', id);
		dispatch('selectChat', { id });
		console.log('[Sidebar] selectChat event dispatched');
	}

	function createNewChat() {
		dispatch('newChat', {});
	}

	function deleteChat(id: string, event: Event) {
		event.stopPropagation();
		dispatch('deleteChat', { id });
	}

	function toggleMinimize() {
		dispatch('toggleMinimize', {});
	}
	
	function toggleKnowledgeBase() {
		console.log('[Sidebar] toggleKnowledgeBase called');
		dispatch('toggleKnowledgeBase', {});
		console.log('[Sidebar] toggleKnowledgeBase event dispatched');
	}
	
	function toggleTags() {
		dispatch('toggleTags', {});
	}

	function truncateText(text: string, maxLength: number = 50) {
		return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
	}
</script>

<div class="{isMinimized ? 'w-16' : 'w-80'} h-full bg-gradient-to-br from-slate-50/95 via-blue-50/90 to-indigo-50/95 backdrop-blur-xl rounded-2xl shadow-xl shadow-blue-200/40 border border-white/30 flex flex-col overflow-hidden transition-all duration-300">
	
	<!-- Minimize Toggle Button -->
	<button
		on:click={toggleMinimize}
		class="absolute top-4 right-4 z-10 p-2 hover:bg-white/20 rounded-lg transition-all duration-200"
		title={isMinimized ? 'Expand sidebar' : 'Minimize sidebar'}
	>
		<svg class="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			{#if isMinimized}
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			{:else}
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			{/if}
		</svg>
	</button>

	{#if isMinimized}
		<!-- Minimized View -->
		<div class="flex flex-col items-center py-6 space-y-4">
			<div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg">
				<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
			</div>
			
			<button
				on:click={createNewChat}
				class="p-3 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-600 hover:from-blue-600 hover:via-indigo-600 hover:to-purple-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-0.5"
				title="New Chat"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
			</button>
			
			<button
				on:click={toggleKnowledgeBase}
				class="p-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-0.5"
				title="Knowledge Base"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
				</svg>
			</button>
			
			<button
				on:click={toggleTags}
				class="p-3 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-0.5"
				title="Tag Management"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
				</svg>
			</button>
		</div>
	{:else}
		<!-- Full View -->
		<!-- Header -->
		<div class="p-6 pb-4 bg-gradient-to-r from-white/40 to-blue-50/60 border-b border-slate-200/30">
			<div class="flex items-center gap-3 mb-6">
				<div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-300/60">
					<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</div>
				<div>
					<h1 class="text-lg font-semibold text-slate-800">SecondBrain</h1>
					<p class="text-xs text-slate-600">AI Assistant</p>
				</div>
			</div>
			
			<div class="flex gap-2">
				<button
					on:click={createNewChat}
					class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-600 hover:from-blue-600 hover:via-indigo-600 hover:to-purple-700 text-white rounded-lg transition-all duration-300 shadow-lg shadow-blue-300/60 hover:shadow-xl hover:shadow-blue-400/70 hover:-translate-y-0.5 font-medium text-sm"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					New Chat
				</button>
				
				<button
					on:click={toggleKnowledgeBase}
					class="px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white rounded-lg transition-all duration-300 shadow-lg shadow-emerald-300/60 hover:shadow-xl hover:shadow-emerald-400/70 hover:-translate-y-0.5 font-medium text-sm"
					title="Knowledge Base"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
					</svg>
				</button>
				
				<button
					on:click={toggleTags}
					class="px-4 py-2.5 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white rounded-lg transition-all duration-300 shadow-lg shadow-orange-300/60 hover:shadow-xl hover:shadow-orange-400/70 hover:-translate-y-0.5 font-medium text-sm"
					title="Tag Management"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Chat List -->
		<div class="flex-1 overflow-y-auto px-4 bg-gradient-to-b from-transparent to-slate-50/50">
		{#if chats.length > 0}
			<div class="pb-6">
				<h2 class="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-4 px-2">Recent Chats</h2>
				<div class="space-y-3">
					{#each chats as chat (chat.id)}
						<div
							class="group relative p-3 rounded-xl cursor-pointer transition-all duration-300 {
								currentChatId === chat.id 
									? 'bg-gradient-to-r from-blue-100/80 via-indigo-50/80 to-purple-100/80 shadow-lg shadow-blue-200/60 border border-blue-300/50' 
									: 'hover:bg-gradient-to-r hover:from-white/80 hover:to-blue-50/60 hover:shadow-md hover:shadow-slate-300/40 hover:-translate-y-0.5 border border-transparent hover:border-slate-300/40'
							}"
							on:click={() => selectChat(chat.id)}
							role="button"
							tabindex="0"
							on:keydown={(e) => e.key === 'Enter' && selectChat(chat.id)}
						>
							<div class="flex items-start justify-between">
								<div class="flex-1 min-w-0 pr-3">
									<div class="text-sm font-semibold text-slate-800 truncate mb-1">
										{chat.title}
									</div>
									<div class="text-xs text-slate-600 truncate mb-2 leading-relaxed">
										{truncateText(chat.last_message || 'No messages yet', 45)}
									</div>
									<div class="text-xs text-slate-500 font-medium">
										{new Date(chat.updated_at).toLocaleDateString([], { 
											month: 'short', 
											day: 'numeric',
											hour: '2-digit',
											minute: '2-digit'
										})}
									</div>
								</div>
								
								<button
									on:click={(e) => deleteChat(chat.id, e)}
									class="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-100/80 hover:text-red-600 rounded-lg transition-all duration-200"
									title="Delete chat"
								>
									<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
									</svg>
								</button>
							</div>
							
							{#if currentChatId === chat.id}
								<div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 via-indigo-500 to-purple-600 rounded-r-full"></div>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center h-full px-6 text-center">
				<div class="w-16 h-16 bg-gradient-to-br from-slate-200/80 to-blue-200/80 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-slate-300/50">
					<svg class="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
					</svg>
				</div>
				<h3 class="text-sm font-semibold text-slate-800 mb-2">No conversations yet</h3>
				<p class="text-xs text-slate-600 leading-relaxed">Start a new chat to begin your conversation with your AI assistant</p>
			</div>
		{/if}
		</div>
		
		<!-- Footer -->
		<div class="p-4 pt-3 border-t border-slate-200/40 bg-gradient-to-r from-slate-50/60 to-blue-50/40">
			<div class="text-xs text-slate-600 text-center">
				<p class="font-medium">SecondBrain AI</p>
				<p class="mt-1">Your intelligent assistant</p>
			</div>
		</div>
	{/if}
</div>