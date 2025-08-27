import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

interface User {
	id: string;
	username: string;
	created_at: string;
}

interface AuthState {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

const initialState: AuthState = {
	user: null,
	token: null,
	isAuthenticated: false,
	isLoading: true
};

export const authStore = writable<AuthState>(initialState);

class AuthService {
	private static instance: AuthService;

	static getInstance(): AuthService {
		if (!AuthService.instance) {
			AuthService.instance = new AuthService();
		}
		return AuthService.instance;
	}

	async init() {
		if (!browser) return;

		const token = localStorage.getItem('auth_token');
		if (!token) {
			authStore.set({ ...initialState, isLoading: false });
			return;
		}

		try {
			// Verify token by fetching user info
			const response = await fetch('/api/v1/auth/me', {
				headers: {
					'Authorization': `Bearer ${token}`
				}
			});

			if (!response.ok) {
				throw new Error('Token invalid');
			}

			const user = await response.json();
			authStore.set({
				user,
				token,
				isAuthenticated: true,
				isLoading: false
			});
		} catch (error) {
			// Token is invalid, clear it
			this.logout();
		}
	}

	async login(username: string, password: string): Promise<void> {
		const response = await fetch('/api/v1/auth/login', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({ username, password })
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Login failed');
		}

		const data = await response.json();
		
		if (browser) {
			localStorage.setItem('auth_token', data.access_token);
			localStorage.setItem('token_type', data.token_type);
		}

		// Get user info
		const userResponse = await fetch('/api/v1/auth/me', {
			headers: {
				'Authorization': `Bearer ${data.access_token}`
			}
		});

		const user = await userResponse.json();

		authStore.set({
			user,
			token: data.access_token,
			isAuthenticated: true,
			isLoading: false
		});
	}

	logout() {
		if (browser) {
			localStorage.removeItem('auth_token');
			localStorage.removeItem('token_type');
		}

		authStore.set({ ...initialState, isLoading: false });
		goto('/login');
	}

	getAuthHeaders(): Record<string, string> {
		const token = browser ? localStorage.getItem('auth_token') : null;
		if (!token) return {};
		
		return {
			'Authorization': `Bearer ${token}`
		};
	}
}

export const authService = AuthService.getInstance();