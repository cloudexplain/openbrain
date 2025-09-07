<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import favicon from '$lib/assets/favicon.svg';
	import '../app.pcss';
	import { authStore, authService } from '$lib/stores/auth';
	import Sidebar from "$lib/components/Sidebar.svelte";
	import KnowledgeBase from "$lib/components/KnowledgeBase.svelte";
	import TagManager from "$lib/components/TagManager.svelte";
	import Notification from "$lib/components/Notification.svelte";
	import type { ChatListItem } from "$lib/api";

	let { children, data } = $props();

	// Public routes that don't require authentication
	const publicRoutes = ['/login', '/signup', '/verify-email'];
	
	// Layout state
	let chats = $state(data?.chats || []);
	let currentChatId: string | null = null;
	let sidebarMinimized = false;
	let viewMode: "chat" | "knowledge" | "tags" = "chat";
	let documents = $state(data?.documents || []);

	// Push notifications
	let pushNotifications: Array<{
		id: number;
		message: string;
		type: "success" | "error" | "info" | "processing";
		duration: number;
	}> = [];
	let notificationId = 0;

	onMount(async () => {
		// Initialize auth service
		await authService.init();

		// Subscribe to auth changes
		authStore.subscribe((auth) => {
			if (!auth.isLoading) {
				const currentPath = $page.url.pathname;
				const isPublicRoute = publicRoutes.includes(currentPath);
				
				if (!auth.isAuthenticated && !isPublicRoute) {
					goto('/login');
				} else if (auth.isAuthenticated && currentPath === '/login') {
					goto('/');
				}
			}
		});
	});

	function showNotification(
		message: string,
		type: "success" | "error" | "info" | "processing" = "info",
		duration: number = 5000,
	) {
		const id = notificationId++;
		pushNotifications = [
			...pushNotifications,
			{ id, message, type, duration },
		];
	}

	function removeNotification(id: number) {
		pushNotifications = pushNotifications.filter((n) => n.id !== id);
	}

	async function handleNewChat() {
		try {
			// Create a new chat on the server
			const response = await fetch("/api/v1/chats", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...authService.getAuthHeaders()
				},
				body: JSON.stringify({
					title: "New Chat",
				}),
			});

			if (!response.ok) {
				throw new Error(`Failed to create chat: ${response.status}`);
			}

			const newChat = await response.json();
			console.log("Created new chat:", newChat);

			// Add the new chat to the chats list at the beginning
			chats = [newChat, ...chats];

			// Navigate to the new chat
			goto(`/chat/${newChat.id}`);
			currentChatId = newChat.id;
			viewMode = "chat";
		} catch (error) {
			console.error("Failed to create new chat:", error);
			showNotification("Failed to create new chat", "error");
		}
	}

	async function handleSelectChat(event: CustomEvent<{ id: string }>) {
		const chatId = event.detail.id;
		goto(`/chat/${chatId}`);
		currentChatId = chatId;
		viewMode = "chat";
	}

	async function handleDeleteChat(event: CustomEvent<{ id: string }>) {
		const chatId = event.detail.id;
		
		try {
			// Delete the chat from the server
			const response = await fetch(`/api/v1/chats/${chatId}`, {
				method: "DELETE",
				headers: authService.getAuthHeaders()
			});

			if (!response.ok) {
				throw new Error(`Failed to delete chat: ${response.status}`);
			}

			// Remove from local state
			chats = chats.filter(chat => chat.id !== chatId);
			
			// Navigate away if we're currently viewing the deleted chat
			if (currentChatId === chatId) {
				currentChatId = null;
				goto('/');
			}
			
			showNotification("Chat deleted successfully", "success");
		} catch (error) {
			console.error("Failed to delete chat:", error);
			showNotification("Failed to delete chat", "error");
		}
	}

	function handleToggleMinimize() {
		sidebarMinimized = !sidebarMinimized;
	}

	function toggleViewMode() {
		goto('/knowledge');
		viewMode = "knowledge";
	}

	function toggleTagsMode() {
		goto('/tags');
		viewMode = "tags";
	}

	function handleKnowledgeBaseClose() {
		viewMode = "chat";
		goto('/');
	}

	function handleTagManagerClose() {
		viewMode = "chat";
		goto('/');
	}

	// Reactive statements using Svelte 5 syntax
	let isPublicRoute = $derived(publicRoutes.includes($page.url.pathname));
	// Show full layout unless we're on a public route (login, signup, etc.)
	let showFullLayout = $derived(!isPublicRoute);

	// Effect to update data from server when it changes
	$effect(() => {
		if (data?.chats) {
			chats = data.chats;
		}
		if (data?.documents) {
			documents = data.documents;
		}
	});

	// Effect to update viewMode and currentChatId based on route changes
	$effect(() => {
		if ($page.url.pathname.startsWith('/knowledge')) {
			viewMode = "knowledge";
			currentChatId = null;
		} else if ($page.url.pathname.startsWith('/tags')) {
			viewMode = "tags";
			currentChatId = null;
		} else if ($page.url.pathname.startsWith('/chat/')) {
			viewMode = "chat";
			// Extract chat ID from the route
			const pathParts = $page.url.pathname.split('/');
			if (pathParts.length >= 3 && pathParts[1] === 'chat') {
				currentChatId = pathParts[2];
			}
		} else {
			viewMode = "chat";
			currentChatId = null;
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if showFullLayout}
	<!-- Full layout for authenticated users -->
	<main class="flex h-screen bg-gray-100">
		<!-- Sidebar -->
		<div class="flex-shrink-0 {sidebarMinimized ? 'w-16' : 'w-80'} transition-all duration-300 ease-in-out">
			<Sidebar
				{chats}
				{currentChatId}
				isMinimized={sidebarMinimized}
				on:newChat={handleNewChat}
				on:selectChat={handleSelectChat}
				on:deleteChat={handleDeleteChat}
				on:toggleMinimize={handleToggleMinimize}
				on:toggleKnowledgeBase={toggleViewMode}
				on:toggleTags={toggleTagsMode}
			/>
		</div>

		<!-- Main Content Area -->
		<div class="flex-1 flex flex-col min-w-0">
			{#if $page.url.pathname === '/knowledge'}
				<!-- Show knowledge base modal for /knowledge root -->
				<KnowledgeBase
					{documents}
					on:close={handleKnowledgeBaseClose}
				/>
			{:else if $page.url.pathname === '/tags'}
				<!-- Show tag manager for /tags route -->
				<TagManager on:close={handleTagManagerClose} />
			{:else}
				<!-- Always render page content for all other routes (including /chat/[id]) -->
				{@render children?.()}
			{/if}
		</div>

		<!-- Push Notifications -->
		<div class="fixed top-4 right-4 z-50 space-y-2">
			{#each pushNotifications as notification (notification.id)}
				<Notification
					message={notification.message}
					type={notification.type}
					duration={notification.duration}
					on:close={() => removeNotification(notification.id)}
				/>
			{/each}
		</div>
	</main>
{:else}
	<!-- Simple layout for public pages -->
	{@render children?.()}
{/if}
