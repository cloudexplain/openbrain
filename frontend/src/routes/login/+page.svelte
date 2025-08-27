<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	let username = '';
	let password = '';
	let isLoading = false;
	let errorMessage = '';

	onMount(() => {
		// Check if user is already authenticated
		const token = localStorage.getItem('auth_token');
		if (token) {
			goto('/');
		}
	});

	async function handleLogin() {
		if (!username || !password) {
			errorMessage = 'Please enter both username and password';
			return;
		}

		isLoading = true;
		errorMessage = '';

		try {
			const response = await fetch('/api/v1/auth/login', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					username,
					password
				})
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Login failed');
			}

			const data = await response.json();
			
			// Store the token
			localStorage.setItem('auth_token', data.access_token);
			localStorage.setItem('token_type', data.token_type);

			// Redirect to main page
			goto('/');

		} catch (error) {
			errorMessage = error.message || 'Login failed. Please try again.';
		} finally {
			isLoading = false;
		}
	}

	function handleSubmit(event: Event) {
		event.preventDefault();
		handleLogin();
	}
</script>

<svelte:head>
	<title>Login - SecondBrain</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30 flex items-center justify-center p-4">
	<div class="bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-white/20 backdrop-blur-sm w-full max-w-md p-8">
		<!-- Logo/Title -->
		<div class="text-center mb-8">
			<div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/25">
				<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
			</div>
			<h1 class="text-2xl font-semibold text-gray-900 mb-2">Welcome to SecondBrain</h1>
			<p class="text-gray-600">Sign in to access your knowledge base</p>
			<p class="mt-2 text-sm text-gray-500">
				Don't have an account? 
				<a href="/signup" class="font-medium text-blue-600 hover:text-blue-500">
					Sign up
				</a>
			</p>
		</div>

		<!-- Login Form -->
		<form on:submit={handleSubmit} class="space-y-6">
			<!-- Username Field -->
			<div>
				<label for="username" class="block text-sm font-medium text-gray-700 mb-2">
					Username or Email
				</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					disabled={isLoading}
					class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
					placeholder="Enter your username or email"
					required
				/>
			</div>

			<!-- Password Field -->
			<div>
				<label for="password" class="block text-sm font-medium text-gray-700 mb-2">
					Password
				</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					disabled={isLoading}
					class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
					placeholder="Enter your password"
					required
				/>
			</div>

			<!-- Error Message -->
			{#if errorMessage}
				<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
					{errorMessage}
				</div>
			{/if}

			<!-- Submit Button -->
			<button
				type="submit"
				disabled={isLoading}
				class="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium py-3 px-4 rounded-lg transition-all duration-200 disabled:cursor-not-allowed flex items-center justify-center"
			>
				{#if isLoading}
					<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Signing in...
				{:else}
					Sign In
				{/if}
			</button>
		</form>

		<!-- Footer -->
		<div class="mt-8 pt-6 border-t border-gray-200 text-center">
			<p class="text-sm text-gray-500">
				Secure, private, and always available.
			</p>
		</div>
	</div>
</div>

<style>
	/* Custom styles if needed */
</style>