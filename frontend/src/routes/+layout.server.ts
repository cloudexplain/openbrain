import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, url }) => {
	// Only load chats for authenticated routes (not login/signup/verify-email)
	const publicRoutes = ['/login', '/signup', '/verify-email'];
	const isPublicRoute = publicRoutes.includes(url.pathname);
	
	if (isPublicRoute) {
		return {
			chats: [],
			documents: []
		};
	}

	try {
		// Load chats for sidebar
		const chatsResponse = await fetch('/api/v1/chats');
		let chats = [];
		if (chatsResponse.ok) {
			chats = await chatsResponse.json();
		}

		// Load documents for knowledge base
		const docsResponse = await fetch('/api/v1/documents');
		let documents = [];
		if (docsResponse.ok) {
			const data = await docsResponse.json();
			documents = Array.isArray(data) ? data : (data.documents || []);
		}

		return {
			chats,
			documents
		};
	} catch (error) {
		console.error('Error loading layout data:', error);
		return {
			chats: [],
			documents: []
		};
	}
};