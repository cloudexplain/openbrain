<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	
	let username = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let error = '';
	let loading = false;
	let showPassword = false;
	let showConfirmPassword = false;
	
	// Validation states
	let usernameError = '';
	let emailError = '';
	let passwordError = '';
	let confirmPasswordError = '';
	
	function validateUsername() {
		if (username.length < 3) {
			usernameError = 'Username must be at least 3 characters';
		} else if (username.length > 50) {
			usernameError = 'Username must be less than 50 characters';
		} else if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
			usernameError = 'Username can only contain letters, numbers, hyphens and underscores';
		} else {
			usernameError = '';
		}
	}
	
	function validateEmail() {
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!emailRegex.test(email)) {
			emailError = 'Please enter a valid email address';
		} else {
			emailError = '';
		}
	}
	
	function validatePassword() {
		if (password.length < 8) {
			passwordError = 'Password must be at least 8 characters';
		} else {
			passwordError = '';
		}
	}
	
	function validateConfirmPassword() {
		if (password !== confirmPassword) {
			confirmPasswordError = 'Passwords do not match';
		} else {
			confirmPasswordError = '';
		}
	}
	
	async function handleSignup() {
		// Validate all fields
		validateUsername();
		validateEmail();
		validatePassword();
		validateConfirmPassword();
		
		if (usernameError || emailError || passwordError || confirmPasswordError) {
			return;
		}
		
		loading = true;
		error = '';
		
		try {
			const response = await fetch('/api/v1/auth/signup', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include',
				body: JSON.stringify({
					username,
					email,
					password
				})
			});
			
			const data = await response.json();
			
			if (response.ok) {
				// Store token if provided
				if (data.access_token) {
					localStorage.setItem('token', data.access_token);
				}
				
				// Redirect to main page with success message
				goto('/?signup=success&verification=sent');
			} else {
				error = data.detail || 'Signup failed';
				
				// Check for specific errors
				if (data.detail?.includes('Username already registered')) {
					usernameError = 'This username is already taken';
				} else if (data.detail?.includes('Email already registered')) {
					emailError = 'This email is already registered';
				} else if (data.detail?.includes('Maximum user limit')) {
					error = 'Registration is currently closed. We have reached our user limit.';
				}
			}
		} catch (err) {
			error = 'Network error. Please try again later.';
		} finally {
			loading = false;
		}
	}
	
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !loading) {
			handleSignup();
		}
	}
</script>

<svelte:head>
	<title>Sign Up - SecondBrain</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
	<div class="w-full max-w-md space-y-8">
		<div>
			<h2 class="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
				Create your account
			</h2>
			<p class="mt-2 text-center text-sm text-gray-600">
				Or
				<a href="/login" class="font-medium text-indigo-600 hover:text-indigo-500">
					sign in to your existing account
				</a>
			</p>
		</div>
		
		<form class="mt-8 space-y-6" on:submit|preventDefault={handleSignup}>
			{#if error}
				<div class="rounded-md bg-red-50 p-4">
					<p class="text-sm text-red-800">{error}</p>
				</div>
			{/if}
			
			<div class="space-y-4">
				<!-- Username -->
				<div>
					<label for="username" class="block text-sm font-medium text-gray-700">
						Username
					</label>
					<div class="mt-1">
						<input
							id="username"
							name="username"
							type="text"
							autocomplete="username"
							required
							bind:value={username}
							on:blur={validateUsername}
							class="block w-full appearance-none rounded-md border {usernameError ? 'border-red-300' : 'border-gray-300'} px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
						/>
						{#if usernameError}
							<p class="mt-1 text-xs text-red-600">{usernameError}</p>
						{/if}
					</div>
				</div>
				
				<!-- Email -->
				<div>
					<label for="email" class="block text-sm font-medium text-gray-700">
						Email address
					</label>
					<div class="mt-1">
						<input
							id="email"
							name="email"
							type="email"
							autocomplete="email"
							required
							bind:value={email}
							on:blur={validateEmail}
							class="block w-full appearance-none rounded-md border {emailError ? 'border-red-300' : 'border-gray-300'} px-3 py-2 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
						/>
						{#if emailError}
							<p class="mt-1 text-xs text-red-600">{emailError}</p>
						{/if}
					</div>
				</div>
				
				<!-- Password -->
				<div>
					<label for="password" class="block text-sm font-medium text-gray-700">
						Password
					</label>
					<div class="mt-1 relative">
						<input
							id="password"
							name="password"
							type={showPassword ? 'text' : 'password'}
							autocomplete="new-password"
							required
							bind:value={password}
							on:blur={validatePassword}
							on:keydown={handleKeydown}
							class="block w-full appearance-none rounded-md border {passwordError ? 'border-red-300' : 'border-gray-300'} px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
						/>
						<button
							type="button"
							on:click={() => showPassword = !showPassword}
							class="absolute inset-y-0 right-0 flex items-center pr-3"
						>
							{#if showPassword}
								<svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
								</svg>
							{:else}
								<svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
							{/if}
						</button>
						{#if passwordError}
							<p class="mt-1 text-xs text-red-600">{passwordError}</p>
						{/if}
					</div>
				</div>
				
				<!-- Confirm Password -->
				<div>
					<label for="confirm-password" class="block text-sm font-medium text-gray-700">
						Confirm Password
					</label>
					<div class="mt-1 relative">
						<input
							id="confirm-password"
							name="confirm-password"
							type={showConfirmPassword ? 'text' : 'password'}
							autocomplete="new-password"
							required
							bind:value={confirmPassword}
							on:blur={validateConfirmPassword}
							on:keydown={handleKeydown}
							class="block w-full appearance-none rounded-md border {confirmPasswordError ? 'border-red-300' : 'border-gray-300'} px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
						/>
						<button
							type="button"
							on:click={() => showConfirmPassword = !showConfirmPassword}
							class="absolute inset-y-0 right-0 flex items-center pr-3"
						>
							{#if showConfirmPassword}
								<svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
								</svg>
							{:else}
								<svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
							{/if}
						</button>
						{#if confirmPasswordError}
							<p class="mt-1 text-xs text-red-600">{confirmPasswordError}</p>
						{/if}
					</div>
				</div>
			</div>
			
			<div>
				<button
					type="submit"
					disabled={loading}
					class="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
				>
					{#if loading}
						<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Creating account...
					{:else}
						Sign up
					{/if}
				</button>
			</div>
			
			<div class="text-sm text-center text-gray-600">
				By signing up, you agree to receive a verification email to activate your account.
			</div>
		</form>
	</div>
</div>