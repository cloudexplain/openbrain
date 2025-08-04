<script lang="ts">
	import { onMount } from 'svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ChatMessage from '$lib/components/ChatMessage.svelte';
	import MessageInput from '$lib/components/MessageInput.svelte';
	import LoadingIndicator from '$lib/components/LoadingIndicator.svelte';
	import { apiClient, type Message, type ChatListItem, type StreamResponse } from '$lib/api';

	let messages: Message[] = [];
	let chats: ChatListItem[] = [];
	let currentChatId: string | null = null;
	let isLoading = false;
	let streamingMessage = '';
	let isSidebarMinimized = false;

	onMount(async () => {
		await loadChats();
	});

	async function loadChats() {
		try {
			chats = await apiClient.getChats();
		} catch (error) {
			console.error('Failed to load chats:', error);
		}
	}

	async function handleSendMessage(event: CustomEvent<{ content: string }>) {
		const userMessage: Message = {
			id: crypto.randomUUID(),
			content: event.detail.content,
			role: 'user',
			timestamp: new Date(),
			chat_id: currentChatId || ''
		};

		messages = [...messages, userMessage];
		isLoading = true;
		streamingMessage = '';

		try {
			const stream = await apiClient.sendMessage(event.detail.content, currentChatId || undefined);
			const reader = stream.getReader();
			
			let assistantMessage: Message | null = null;
			
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const response: StreamResponse = value;
				
				if (response.type === 'content' && response.content) {
					streamingMessage += response.content;
				} else if (response.type === 'done') {
					// Create the final assistant message
					assistantMessage = {
						id: response.message_id || crypto.randomUUID(),
						content: streamingMessage,
						role: 'assistant',
						timestamp: new Date(),
						chat_id: response.chat_id || currentChatId || ''
					};
					
					messages = [...messages, assistantMessage];
					streamingMessage = '';
					
					// Update chat ID if this was a new chat
					if (response.chat_id && !currentChatId) {
						currentChatId = response.chat_id;
					}
					
					// Reload chats to update sidebar
					await loadChats();
				} else if (response.type === 'error') {
					console.error('Streaming error:', response.error);
					streamingMessage = '';
				}
			}
		} catch (error) {
			console.error('Failed to send message:', error);
			streamingMessage = '';
		} finally {
			isLoading = false;
		}
	}

	async function handleNewChat() {
		currentChatId = null;
		messages = [];
		streamingMessage = '';
	}

	async function handleSelectChat(event: CustomEvent<{ id: string }>) {
		currentChatId = event.detail.id;
		streamingMessage = '';
		
		try {
			const chat = await apiClient.getChat(event.detail.id);
			messages = chat.messages;
		} catch (error) {
			console.error('Failed to load chat messages:', error);
			messages = [];
		}
	}

	async function handleDeleteChat(event: CustomEvent<{ id: string }>) {
		try {
			await apiClient.deleteChat(event.detail.id);
			
			// Remove from local state
			chats = chats.filter(chat => chat.id !== event.detail.id);
			
			// Clear current chat if it was deleted
			if (currentChatId === event.detail.id) {
				await handleNewChat();
			}
		} catch (error) {
			console.error('Failed to delete chat:', error);
		}
	}

	function handleToggleMinimize() {
		isSidebarMinimized = !isSidebarMinimized;
	}

	async function handleSuggestedPrompt(prompt: string) {
		await handleSendMessage(new CustomEvent('send', { detail: { content: prompt } }));
	}
</script>

<div class="flex h-screen bg-gradient-to-br from-slate-50 to-blue-50/30 p-4 gap-4">
	<!-- Sidebar -->
	<div class="transition-all duration-300" class:w-80={!isSidebarMinimized} class:w-16={isSidebarMinimized}>
		<Sidebar 
			bind:isMinimized={isSidebarMinimized}
			{chats} 
			{currentChatId}
			on:newChat={handleNewChat}
			on:selectChat={handleSelectChat}
			on:deleteChat={handleDeleteChat}
			on:toggleMinimize={handleToggleMinimize}
		/>
	</div>

	<!-- Main Chat Area -->
	<div class="flex-1 flex flex-col bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-white/20 backdrop-blur-sm overflow-hidden">
		<!-- Chat Messages -->
		<div class="flex-1 overflow-y-auto">
			{#if messages.length === 0 && !isLoading && !streamingMessage}
				<div class="flex items-center justify-center h-full p-8">
					<div class="text-center max-w-2xl">
						<div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-blue-500/25">
							<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
							</svg>
						</div>
						<h2 class="text-2xl font-semibold text-gray-900 mb-4">Welcome to SecondBrain</h2>
						<p class="text-base text-gray-600 mb-8 leading-relaxed">
							Your intelligent assistant for analysis, writing, coding, and creative projects. How can I help you today?
						</p>
						
						<!-- Suggested Prompts -->
						<div class="grid gap-4 mb-8 max-w-lg mx-auto">
							<button 
								on:click={() => handleSuggestedPrompt("Help me brainstorm creative ideas")}
								class="group p-5 text-left bg-white hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 rounded-2xl shadow-md hover:shadow-xl shadow-slate-200/50 hover:shadow-blue-200/30 transition-all duration-300 hover:-translate-y-0.5 border border-slate-100 hover:border-blue-200"
							>
								<div class="flex items-center gap-4">
									<div class="w-10 h-10 bg-gradient-to-br from-orange-400 to-pink-500 rounded-xl flex items-center justify-center shadow-lg shadow-orange-200/50">
										<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
										</svg>
									</div>
									<span class="text-base font-medium text-gray-700 group-hover:text-gray-900">Help me brainstorm creative ideas</span>
								</div>
							</button>
							
							<button 
								on:click={() => handleSuggestedPrompt("Explain a complex topic simply")}
								class="group p-5 text-left bg-white hover:bg-gradient-to-r hover:from-green-50 hover:to-teal-50 rounded-2xl shadow-md hover:shadow-xl shadow-slate-200/50 hover:shadow-green-200/30 transition-all duration-300 hover:-translate-y-0.5 border border-slate-100 hover:border-green-200"
							>
								<div class="flex items-center gap-4">
									<div class="w-10 h-10 bg-gradient-to-br from-green-400 to-teal-500 rounded-xl flex items-center justify-center shadow-lg shadow-green-200/50">
										<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
										</svg>
									</div>
									<span class="text-base font-medium text-gray-700 group-hover:text-gray-900">Explain a complex topic simply</span>
								</div>
							</button>
							
							<button 
								on:click={() => handleSuggestedPrompt("Help me write better code")}
								class="group p-5 text-left bg-white hover:bg-gradient-to-r hover:from-indigo-50 hover:to-blue-50 rounded-2xl shadow-md hover:shadow-xl shadow-slate-200/50 hover:shadow-indigo-200/30 transition-all duration-300 hover:-translate-y-0.5 border border-slate-100 hover:border-indigo-200"
							>
								<div class="flex items-center gap-4">
									<div class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200/50">
										<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
										</svg>
									</div>
									<span class="text-base font-medium text-gray-700 group-hover:text-gray-900">Help me write better code</span>
								</div>
							</button>
						</div>
						
						<p class="text-sm text-gray-500">
							AI responses may contain errors. Please verify important information.
						</p>
					</div>
				</div>
			{:else}
				<div class="pb-32">
					{#each messages as message (message.id)}
						<ChatMessage {message} />
					{/each}
					
					{#if isLoading}
						<LoadingIndicator type="typing" />
					{/if}
					
					{#if streamingMessage}
						<ChatMessage message={{
							id: 'streaming',
							content: streamingMessage,
							role: 'assistant',
							timestamp: new Date()
						}} />
					{/if}
				</div>
			{/if}
		</div>

		<!-- Message Input -->
		<MessageInput 
			disabled={isLoading || streamingMessage !== ''}
			on:send={handleSendMessage}
		/>
	</div>
</div>
