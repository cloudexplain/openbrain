import type { PageServerLoad, Actions } from './$types';
import { fail, redirect } from '@sveltejs/kit';
import type { Cookies } from '@sveltejs/kit';
import { getAuthHeaders } from '../lib/utils';
//
// Helper function to get auth headers for backend requests

export const load: PageServerLoad = async ({ cookies }) => {
	console.log('[+page.server.ts] Loading page data...');
	
	const authHeaders = getAuthHeaders(cookies);
	console.log('[+page.server.ts] Session cookie:', cookies.get('sessionid') ? 'present' : 'missing');
	
	try {
		// Fetch both chats and documents in parallel, forwarding cookies
		const [chatsResponse, documentsResponse] = await Promise.all([
			fetch('http://backend:8000/api/v1/chats', {
				headers: authHeaders
			}),
			fetch('http://backend:8000/api/v1/documents', {
				headers: authHeaders
			})
		]);
		
		// Check for verification required on chats response
		if (!chatsResponse.ok) {
			if (chatsResponse.status === 403) {
				const verificationRequired = chatsResponse.headers.get('X-Verification-Required');
				if (verificationRequired === 'true') {
					// Redirect to verification page
					throw redirect(302, '/verify-email');
				}
			}
			throw new Error(`Failed to load chats: ${chatsResponse.status}`);
		}
		
		// Check for verification required on documents response  
		if (!documentsResponse.ok) {
			if (documentsResponse.status === 403) {
				const verificationRequired = documentsResponse.headers.get('X-Verification-Required');
				if (verificationRequired === 'true') {
					// Redirect to verification page
					throw redirect(302, '/verify-email');
				}
			}
			throw new Error(`Failed to load documents: ${documentsResponse.status}`);
		}
		
		const chats = await chatsResponse.json();
		const documents = await documentsResponse.json();
		
		console.log('[+page.server.ts] Got chats:', chats);
		console.log('[+page.server.ts] Got documents:', documents);
		
		return {
			chats: chats || [],
			documents: documents || []
		};
	} catch (error) {
		console.error('[+page.server.ts] Error loading data:', error);
		return {
			chats: [],
			documents: []
		};
	}
};
