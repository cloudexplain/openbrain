<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import favicon from '$lib/assets/favicon.svg';
	import '../app.pcss';
	import { authStore, authService } from '$lib/stores/auth';

	let { children } = $props();

	// Public routes that don't require authentication
	const publicRoutes = ['/login', '/signup', '/verify-email'];

	onMount(async () => {
		// Initialize auth service
		await authService.init();

		// Check if current route requires authentication
		const currentPath = $page.url.pathname;
		const isPublicRoute = publicRoutes.includes(currentPath);

		// Subscribe to auth changes
		authStore.subscribe((auth) => {
			if (!auth.isLoading) {
				if (!auth.isAuthenticated && !isPublicRoute) {
					goto('/login');
				} else if (auth.isAuthenticated && currentPath === '/login') {
					goto('/');
				}
			}
		});
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children?.()}
