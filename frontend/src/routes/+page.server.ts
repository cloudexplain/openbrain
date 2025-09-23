import type { PageServerLoad, Actions } from './$types';
import { fail, redirect } from '@sveltejs/kit';
//
// Helper function to get auth headers for backend requests

export const load: PageServerLoad = async ({ cookies }) => {
	console.log('[+page.server.ts] Loading page data...');
	
	try {
		// Fetch both chats and documents in parallel, forwarding cookies
		const [chatsResponse, documentsResponse] = await Promise.all([
			fetch('http://backend:8000/api/v1/chats', {
				headers: {}
			}),
			fetch('http://backend:8000/api/v1/documents', {
				headers: {}
		]);
		
		
		
		
		
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
