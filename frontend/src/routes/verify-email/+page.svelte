<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	
	let verifying = true;
	let verified = false;
	let error = '';
	let resending = false;
	let resendMessage = '';
	let resendError = '';
	let countdown = 0;
	let countdownInterval: NodeJS.Timeout;
	
	onMount(async () => {
		// Get token from URL query params
		const token = $page.url.searchParams.get('token');
		
		if (token) {
			// Verify the token
			await verifyEmail(token);
		} else {
			// No token provided, show resend form
			verifying = false;
			error = 'No verification token provided';
			await checkVerificationStatus();
		}
		
		// Cleanup on unmount
		return () => {
			if (countdownInterval) {
				clearInterval(countdownInterval);
			}
		};
	});
	
	async function verifyEmail(token: string) {
		try {
			const response = await fetch(`/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`, {
				method: 'POST',
				credentials: 'include'
			});
			
			const data = await response.json();
			
			if (response.ok) {
				verified = true;
				error = '';
				
				// Redirect to main page after 3 seconds
				setTimeout(() => {
					goto('/?verified=true');
				}, 3000);
			} else {
				error = data.detail || 'Invalid or expired verification token';
			}
		} catch (err) {
			error = 'Network error. Please try again later.';
		} finally {
			verifying = false;
		}
	}
	
	async function checkVerificationStatus() {
		try {
			const token = localStorage.getItem('token');
			if (!token) return;
			
			const response = await fetch('/api/v1/auth/verification-status', {
				headers: {
					'Authorization': `Bearer ${token}`
				},
				credentials: 'include'
			});
			
			if (response.ok) {
				const data = await response.json();
				if (data.is_verified) {
					verified = true;
					error = '';
					setTimeout(() => {
						goto('/');
					}, 3000);
				}
			}
		} catch (err) {
			// Ignore errors in status check
		}
	}
	
	async function resendVerificationEmail() {
		resending = true;
		resendMessage = '';
		resendError = '';
		
		try {
			const token = localStorage.getItem('token');
			if (!token) {
				resendError = 'Please log in to resend verification email';
				return;
			}
			
			const response = await fetch('/api/v1/auth/resend-verification', {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${token}`
				},
				credentials: 'include'
			});
			
			const data = await response.json();
			
			if (response.ok) {
				resendMessage = data.message || 'Verification email sent successfully';
				
				// Show remaining attempts
				if (data.remaining_this_hour !== undefined) {
					resendMessage += ` (${data.remaining_this_hour} resends remaining this hour)`;
				}
			} else if (response.status === 429) {
				// Rate limited
				resendError = data.detail || 'Too many requests. Please try again later.';
				
				// Get retry-after header and start countdown
				const retryAfter = response.headers.get('Retry-After');
				if (retryAfter) {
					startCountdown(parseInt(retryAfter));
				}
			} else {
				resendError = data.detail || 'Failed to resend verification email';
			}
		} catch (err) {
			resendError = 'Network error. Please try again later.';
		} finally {
			resending = false;
		}
	}
	
	function startCountdown(seconds: number) {
		countdown = seconds;
		
		countdownInterval = setInterval(() => {
			countdown--;
			if (countdown <= 0) {
				clearInterval(countdownInterval);
			}
		}, 1000);
	}
	
	function formatCountdown(seconds: number) {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>Verify Email - SecondBrain</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
	<div class="w-full max-w-md space-y-8">
		<div class="text-center">
			{#if verifying}
				<!-- Verifying state -->
				<div class="flex justify-center">
					<svg class="animate-spin h-12 w-12 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				</div>
				<h2 class="mt-6 text-2xl font-bold text-gray-900">Verifying your email...</h2>
				<p class="mt-2 text-gray-600">Please wait while we verify your email address.</p>
				
			{:else if verified}
				<!-- Success state -->
				<div class="flex justify-center">
					<div class="rounded-full bg-green-100 p-3">
						<svg class="h-12 w-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
					</div>
				</div>
				<h2 class="mt-6 text-2xl font-bold text-gray-900">Email Verified!</h2>
				<p class="mt-2 text-gray-600">Your email has been successfully verified.</p>
				<p class="mt-4 text-sm text-gray-500">Redirecting you to the app...</p>
				
			{:else}
				<!-- Error/Resend state -->
				<div class="flex justify-center">
					<div class="rounded-full bg-yellow-100 p-3">
						<svg class="h-12 w-12 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
						</svg>
					</div>
				</div>
				<h2 class="mt-6 text-2xl font-bold text-gray-900">Email Verification Required</h2>
				
				{#if error}
					<div class="mt-4 rounded-md bg-red-50 p-4">
						<p class="text-sm text-red-800">{error}</p>
					</div>
				{/if}
				
				<div class="mt-8 space-y-4">
					<p class="text-gray-600">
						Please check your email for the verification link. If you didn't receive it:
					</p>
					
					<ul class="text-left text-sm text-gray-600 space-y-2">
						<li class="flex items-start">
							<svg class="h-5 w-5 text-gray-400 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Check your spam/junk folder
						</li>
						<li class="flex items-start">
							<svg class="h-5 w-5 text-gray-400 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Make sure the email address is correct
						</li>
						<li class="flex items-start">
							<svg class="h-5 w-5 text-gray-400 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Wait a few minutes for the email to arrive
						</li>
					</ul>
					
					{#if resendMessage}
						<div class="rounded-md bg-green-50 p-4">
							<p class="text-sm text-green-800">{resendMessage}</p>
						</div>
					{/if}
					
					{#if resendError}
						<div class="rounded-md bg-red-50 p-4">
							<p class="text-sm text-red-800">{resendError}</p>
						</div>
					{/if}
					
					<div class="flex flex-col space-y-3">
						<button
							on:click={resendVerificationEmail}
							disabled={resending || countdown > 0}
							class="flex w-full justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{#if resending}
								<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								Sending...
							{:else if countdown > 0}
								Resend available in {formatCountdown(countdown)}
							{:else}
								Resend Verification Email
							{/if}
						</button>
						
						<a
							href="/login"
							class="flex w-full justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
						>
							Back to Login
						</a>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>