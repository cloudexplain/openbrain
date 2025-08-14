<script lang="ts">
	import { onMount } from 'svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ChatMessage from '$lib/components/ChatMessage.svelte';
	import MessageInput from '$lib/components/MessageInput.svelte';
	import LoadingIndicator from '$lib/components/LoadingIndicator.svelte';
	import KnowledgeEditModal from '$lib/components/KnowledgeEditModal.svelte';
	import Notification from '$lib/components/Notification.svelte';
	import KnowledgeBase from '$lib/components/KnowledgeBase.svelte';
	import type { Message, ChatListItem, StreamResponse } from '$lib/api';
	
	// Get data from server
	export let data;

	let messages: Message[] = [];
	let chats: ChatListItem[] = [];
	let currentChatId: string | null = null;
	let isLoading = false;
	let streamingMessage = '';
	let isSidebarMinimized = false;
	let showKnowledgeModal = false;
	let currentChatTitle = '';
	let viewMode: 'chat' | 'knowledge' = 'chat';
	
	// Notification system
	let notifications: Array<{
		id: number;
		message: string;
		type: 'success' | 'error' | 'info';
	}> = [];
	let notificationId = 0;

	onMount(async () => {
		// Use server-provided data instead of making client-side API calls
		chats = data.chats || [];
		console.log('Loaded chats from server:', chats);
	});
	
	function showNotification(message: string, type: 'success' | 'error' | 'info' = 'info') {
		const id = ++notificationId;
		notifications = [...notifications, { id, message, type }];
	}
	
	function removeNotification(id: number) {
		notifications = notifications.filter(n => n.id !== id);
	}

	// No longer needed - using server-side data
	// async function loadChats() {
	//   try {
	//     chats = await apiClient.getChats();
	//     console.log('Loaded chats:', chats);
	//   } catch (error) {
	//     console.error('Failed to load chats:', error);
	//   }
	// }

	const generateUUID = () => {
	  if (crypto.randomUUID) {
	    return crypto.randomUUID();
	  }
	  // Fallback implementation
	  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
	    const r = Math.random() * 16 | 0;
	    const v = c == 'x' ? r : (r & 0x3 | 0x8);
	    return v.toString(16);
	  });
	};


	async function handleSendMessage(event: CustomEvent<{ content: string }>) {
		console.log("BEfore calling random UUID");
		const userMessage: Message = {
			id: generateUUID(),
			content: event.detail.content,
			role: 'user',
			timestamp: new Date(),
			chat_id: currentChatId || ''
		};

		messages = [...messages, userMessage];
		isLoading = true;
		streamingMessage = '';

		try {
			console.log('Sending message to backend');
			
			// Use proxy to call backend service (streaming needs direct connection)
			const response = await fetch('/api/v1/chat', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					message: event.detail.content,
					chat_id: currentChatId || null
				})
			});
			
			console.log('Message response:', response.status, response.statusText);
			
			if (!response.ok) {
				throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
			}
			
			if (!response.body) {
				throw new Error('No response body received');
			}
			
			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			
			let assistantMessage: Message | null = null;
			
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				// Decode the bytes to text and add to buffer
				buffer += decoder.decode(value, { stream: true });
				
				// Process complete lines from the buffer
				const lines = buffer.split('\n');
				buffer = lines.pop() || ''; // Keep the incomplete line in the buffer
				
				for (const line of lines) {
					if (line.startsWith('data: ')) {
						try {
							const jsonStr = line.slice(6); // Remove 'data: '
							if (jsonStr.trim() === '') continue; // Skip empty data lines
							
							const streamResponse: StreamResponse = JSON.parse(jsonStr);
							console.log('Parsed stream response:', streamResponse);
							
							if (streamResponse.type === 'content' && streamResponse.content) {
								streamingMessage += streamResponse.content;
							} else if (streamResponse.type === 'done') {
								// Create the final assistant message
								assistantMessage = {
									id: streamResponse.message_id || generateUUID(),
									content: streamingMessage,
									role: 'assistant',
									timestamp: new Date(),
									chat_id: streamResponse.chat_id || currentChatId || ''
								};
								
								messages = [...messages, assistantMessage];
								streamingMessage = '';
								
								// Update chat ID if this was a new chat
								if (streamResponse.chat_id && !currentChatId) {
									currentChatId = streamResponse.chat_id;
								}
							}
						} catch (error) {
							console.error('Error parsing stream response:', error);
						}
					}
				}
			}
			
			// TODO: Reload chats to update sidebar (implement server-side reload)
			console.log('Message sending completed');
		} catch (error) {
			console.error('Failed to send message:', error);
			console.error('Error type:', error.constructor.name);
			console.error('Error message:', error.message);
			console.error('Full error object:', error);
			
			// Show user-friendly error message
			showNotification(`Failed to send message: ${error.message || 'Network error'}`, 'error');
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
		console.log('[handleSelectChat] Event triggered with ID:', event.detail.id);
		currentChatId = event.detail.id;
		streamingMessage = '';
		
		try {
			console.log('[handleSelectChat] Loading chat messages for:', event.detail.id);
			
			// Use direct API call through proxy
			const response = await fetch(`/api/v1/chats/${event.detail.id}`);
			
			console.log('[handleSelectChat] Response status:', response.status);
			
			if (!response.ok) {
				throw new Error(`Failed to load chat: ${response.status}`);
			}
			
			// Direct JSON parsing - no SvelteKit serialization issues
			const chat = await response.json();
			console.log('[handleSelectChat] Raw chat data:', chat);
			messages = chat.messages || [];
			currentChatTitle = chat.title || '';
			console.log('[handleSelectChat] Set messages:', messages.length, 'messages');
			console.log('[handleSelectChat] Set title:', currentChatTitle);
			console.log('[handleSelectChat] Messages array:', messages);
			
			// Force reactivity update
			messages = [...messages];
		} catch (error) {
			console.error('[handleSelectChat] Error:', error);
			showNotification('Failed to load chat messages', 'error');
			messages = [];
		}
	}

	async function handleDeleteChat(event: CustomEvent<{ id: string }>) {
		try {
			console.log('Deleting chat:', event.detail.id);
			
			const response = await fetch(`/api/v1/chats/${event.detail.id}`, {
				method: 'DELETE'
			});
			
			if (!response.ok) {
				throw new Error(`Failed to delete chat: ${response.status}`);
			}
			
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

	async function handleSaveToKnowledge() {
		if (!currentChatId) {
			showNotification('No chat selected to save', 'error');
			return;
		}

		showKnowledgeModal = true;
	}

	async function handleSaveEditedKnowledge(event: CustomEvent<{ title: string; content: any; mode: string }>) {
		if (!currentChatId) {
			return;
		}

		try {
			const { title, content, mode } = event.detail;
			
			const body: any = {
				title,
				save_mode: mode === 'document' ? 'content' : 'messages'
			};
			
			if (typeof content === 'string') {
				body.content = content;
			} else {
				body.content = content;
			}
			
			const response = await fetch(`/api/v1/chats/${currentChatId}/save-to-knowledge`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(body)
			});
			
			if (!response.ok) {
				throw new Error(`Failed to save: ${response.status}`);
			}
			
			const result = await response.json();
			
			showNotification(`Successfully saved "${title}" to knowledge base! Created ${result.chunks_created} chunks.`, 'success');
			showKnowledgeModal = false;
		} catch (error) {
			console.error('Failed to save chat to knowledge:', error);
			showNotification('Failed to save chat to knowledge base', 'error');
		}
	}

	function handleCancelKnowledgeEdit() {
		showKnowledgeModal = false;
	}
	
	function toggleViewMode() {
		console.log('[toggleViewMode] Current viewMode:', viewMode);
		viewMode = viewMode === 'chat' ? 'knowledge' : 'chat';
		console.log('[toggleViewMode] New viewMode:', viewMode);
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
			on:toggleKnowledgeBase={toggleViewMode}
		/>
	</div>

	<!-- Main Content Area -->
	<div class="flex-1 {viewMode === 'knowledge' ? 'flex' : 'flex flex-col'} bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-white/20 backdrop-blur-sm overflow-hidden" style="height: calc(100vh - 2rem);">
		
		{#if viewMode === 'knowledge'}
			<!-- Knowledge Base View -->
			<KnowledgeBase 
				documents={data.documents || []}
				on:close={() => viewMode = 'chat'} 
				on:notification={(e) => showNotification(e.detail.message, e.detail.type)}
			/>
		{:else}
			<!-- Chat View -->
		
		<!-- Chat Header (only show when there are messages) -->
		{#if currentChatId && messages.length > 0}
			<div class="flex items-center justify-between px-6 py-3 border-b border-gray-100 bg-gray-50/50">
				<div class="text-sm text-gray-600">
					Current conversation ({messages.length} messages)
				</div>
				<button 
					on:click={handleSaveToKnowledge}
					class="flex items-center gap-2 px-3 py-1.5 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors duration-200"
					title="Save this conversation to knowledge base for future reference"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
					</svg>
					Save to Knowledge
				</button>
			</div>
		{/if}
		
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
		{/if}
	</div>
</div>

<!-- Knowledge Edit Modal -->
{#if showKnowledgeModal}
	<KnowledgeEditModal 
		messages={messages}
		chatTitle={currentChatTitle}
		on:save={handleSaveEditedKnowledge}
		on:cancel={handleCancelKnowledgeEdit}
	/>
{/if}

<!-- Notifications -->
{#each notifications as notification (notification.id)}
	<Notification
		message={notification.message}
		type={notification.type}
		onClose={() => removeNotification(notification.id)}
	/>
{/each}
