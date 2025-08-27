<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	
	let showMenu = false;
	let user: any = null;
	let verificationStatus: any = null;
	
	onMount(async () => {
		await fetchUserInfo();
		await fetchVerificationStatus();
	});
	
	async function fetchUserInfo() {
		try {
			const response = await fetch('/api/v1/auth/me', {
				credentials: 'include'
			});
			
			if (response.ok) {
				user = await response.json();
			}
		} catch (err) {
			console.error('Failed to fetch user info:', err);
		}
	}
	
	async function fetchVerificationStatus() {
		try {
			const response = await fetch('/api/v1/auth/verification-status', {
				credentials: 'include'
			});
			
			if (response.ok) {
				verificationStatus = await response.json();
			}
		} catch (err) {
			console.error('Failed to fetch verification status:', err);
		}
	}
	
	async function handleLogout() {
		try {
			const response = await fetch('/api/v1/auth/logout', {
				method: 'POST',
				credentials: 'include'
			});
			
			if (response.ok) {
				localStorage.removeItem('token');
				localStorage.removeItem('auth_token');
				localStorage.removeItem('token_type');
				goto('/login');
			}
		} catch (err) {
			console.error('Logout failed:', err);
		}
	}
	
	function handleClickOutside(event: MouseEvent) {
		if (showMenu && !(event.target as HTMLElement).closest('.user-menu-container')) {
			showMenu = false;
		}
	}
	
	$: if (typeof window !== 'undefined') {
		if (showMenu) {
			document.addEventListener('click', handleClickOutside);
		} else {
			document.removeEventListener('click', handleClickOutside);
		}
	}
</script>

{#if user}
	<div class="user-menu-container relative">
		<button
			on:click|stopPropagation={() => showMenu = !showMenu}
			class="flex items-center space-x-2 text-sm font-medium text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 rounded-md px-3 py-2"
		>
			<div class="w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center">
				{user.username ? user.username[0].toUpperCase() : '?'}
			</div>
			<span>{user.username}</span>
			<svg class="w-4 h-4 transition-transform {showMenu ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>
		
		{#if showMenu}
			<div class="absolute right-0 mt-2 w-64 bg-white rounded-md shadow-lg py-1 z-50 border border-gray-200">
				<!-- User Info Section -->
				<div class="px-4 py-3 border-b border-gray-200">
					<p class="text-sm font-medium text-gray-900">{user.username}</p>
					{#if user.email}
						<p class="text-xs text-gray-500">{user.email}</p>
					{/if}
					
					<!-- Verification Status -->
					{#if verificationStatus}
						<div class="mt-2">
							{#if verificationStatus.is_verified}
								<div class="flex items-center text-xs text-green-600">
									<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									Verified
								</div>
							{:else if verificationStatus.is_within_grace_period}
								<div class="flex items-center text-xs text-yellow-600">
									<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									Verify email soon
								</div>
							{:else}
								<a
									href="/verify-email"
									class="flex items-center text-xs text-red-600 hover:text-red-700"
								>
									<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
									</svg>
									Verify email required
								</a>
							{/if}
						</div>
					{/if}
				</div>
				
				<!-- Menu Items -->
				<div class="py-1">
					{#if verificationStatus && !verificationStatus.is_verified}
						<a
							href="/verify-email"
							class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
						>
							<span class="flex items-center">
								<svg class="w-4 h-4 mr-2 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
								</svg>
								Verify Email
							</span>
						</a>
					{/if}
					
					<button
						on:click={() => { showMenu = false; /* Future: Open account settings */ }}
						class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
					>
						<span class="flex items-center">
							<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
							</svg>
							Account Settings
							<span class="text-xs text-gray-400 ml-1">(Coming soon)</span>
						</span>
					</button>
					
					<div class="border-t border-gray-200 my-1"></div>
					
					<button
						on:click={handleLogout}
						class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
					>
						<span class="flex items-center">
							<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
							</svg>
							Sign Out
						</span>
					</button>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.user-menu-container {
		z-index: 1000;
	}
</style>