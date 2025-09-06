import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, url }) => {
	// Extract document ID
	const documentId = params.id;
	
	// Extract query parameters for highlighting
	const messageId = url.searchParams.get('messageId');
	const chunks = url.searchParams.get('chunks');
	const pages = url.searchParams.get('pages');
	
	// Return initial data - actual document loading happens client-side
	// This allows for dynamic highlight updates without page reload
	// Authentication is handled by the API endpoints themselves
	return {
		documentId,
		messageId,
		chunks: chunks?.split(',') || [],
		pages: pages?.split(',').map(Number) || []
	};
};