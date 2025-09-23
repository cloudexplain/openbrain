import type { LayoutServerLoad } from './$types';
// Server-side code - runs in the SvelteKit server
import type { PageServerLoad, Actions } from './$types';

export const load: LayoutServerLoad = async ({ fetch, url }) => {
	// Load chats and documents for all routes

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



const actions: Actions = {
	uploadDocument: async ({ request, cookies }) => {
		console.log('[+page.server.ts] Upload document action');
		
		try {
			const formData = await request.formData();
			const file = formData.get('file') as File;
			
			if (!file) {
				return fail(400, { error: 'No file provided' });
			}
			
			console.log('[+page.server.ts] Uploading file:', file.name);
			
			// Forward to backend
			const backendFormData = new FormData();
			backendFormData.append('file', file);
			
			console.log("Calling upload document to", 'http://backend:8000/api/v1/documents/upload');
			const response = await fetch('http://backend:8000/api/v1/documents/upload', {
				method: 'POST',
				headers: {},
				body: backendFormData
			});
			
			if (!response.ok) {
				const error = await response.text();
				console.error('[+page.server.ts] Upload failed:', error);
				return fail(response.status, { error: `Upload failed: ${response.statusText}` });
			}
			
			const result = await response.json();
			console.log('[+page.server.ts] Upload success:', result);
			
			return { success: true, ...result };
		} catch (error) {
			console.error('[+page.server.ts] Upload error:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	uploadMultipleDocuments: async ({ request, cookies }) => {
		console.log('[+page.server.ts] Upload multiple documents action');
		
		try {
			const formData = await request.formData();
			const files = formData.getAll('files') as File[];
			
			if (!files || files.length === 0) {
				return fail(400, { error: 'No files provided' });
			}
			
			console.log('[+page.server.ts] Uploading files:', files.map(f => f.name));
			
			// Forward to backend
			const backendFormData = new FormData();
			files.forEach(file => {
				backendFormData.append('files', file);
			});
			
			console.log("Calling upload multiple documents to", 'http://backend:8000/api/v1/documents/upload-multiple');
			const response = await fetch('http://backend:8000/api/v1/documents/upload-multiple', {
				method: 'POST',
				headers: {},
				body: backendFormData
			});
			
			if (!response.ok) {
				const error = await response.text();
				console.error('[+page.server.ts] Multi-upload failed:', error);
				return fail(response.status, { error: `Upload failed: ${response.statusText}` });
			}
			
			const result = await response.json();
			console.log('[+page.server.ts] Multi-upload success:', result);
			
			return { success: true, ...result };
		} catch (error) {
			console.error('[+page.server.ts] Multi-upload error:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	getDocument: async ({ request, cookies }) => {
		const formData = await request.formData();
		const documentId = formData.get('documentId') as string;
		
		try {
			const response = await fetch(`http://backend:8000/api/v1/documents/${documentId}`, {
				headers: {}
			});
			
			if (!response.ok) {
				return fail(response.status, { error: `Failed to load document: ${response.statusText}` });
			}
			
			const document = await response.json();
			return { success: true, document };
		} catch (error) {
			console.error('[+page.server.ts] Error loading document:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	deleteDocument: async ({ request, cookies }) => {
		const formData = await request.formData();
		const documentId = formData.get('documentId') as string;
		
		try {
			const response = await fetch(`http://backend:8000/api/v1/documents/${documentId}`, {
				method: 'DELETE',
				headers: {}
			});
			
			if (!response.ok) {
				return fail(response.status, { error: `Failed to delete document: ${response.statusText}` });
			}
			
			return { success: true };
		} catch (error) {
			console.error('[+page.server.ts] Error deleting document:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	sendMessage: async ({ request, cookies }) => {
		const formData = await request.formData();
		const message = formData.get('message') as string;
		const chatId = formData.get('chatId') as string | null;
		
		console.log('[+page.server.ts] Sending message:', message, 'to chat:', chatId);
		
		try {
			const response = await fetch('http://backend:8000/api/v1/chat', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					message,
					chat_id: chatId
				})
			});
			
			if (!response.ok) {
				const error = await response.text();
				console.error('[+page.server.ts] Send message failed:', error);
				return fail(response.status, { error: `Failed to send message: ${response.statusText}` });
			}
			
			// For streaming responses, we return the stream setup info
			// The actual streaming will be handled client-side
			return { 
				success: true,
				streamUrl: `/api/v1/chat`,
				chatId,
				message
			};
		} catch (error) {
			console.error('[+page.server.ts] Error sending message:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	getChat: async ({ request, cookies }) => {
		const formData = await request.formData();
		const chatId = formData.get('chatId') as string;
		
		console.log('[+page.server.ts] Getting chat:', chatId);
		
		try {
			const response = await fetch(`http://backend:8000/api/v1/chats/${chatId}`, {
				headers: {}
			});
			
			if (!response.ok) {
				return fail(response.status, { error: `Failed to load chat: ${response.statusText}` });
			}
			
			const chat = await response.json();
			console.log("Server side chat", chat);
			return { chatData: JSON.stringify(chat) };
		} catch (error) {
			console.error('[+page.server.ts] Error loading chat:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	deleteChat: async ({ request, cookies }) => {
		const formData = await request.formData();
		const chatId = formData.get('chatId') as string;
		
		console.log('[+page.server.ts] Deleting chat:', chatId);
		
		try {
			const response = await fetch(`http://backend:8000/api/v1/chats/${chatId}`, {
				method: 'DELETE',
				headers: {}
			});
			
			if (!response.ok) {
				return fail(response.status, { error: `Failed to delete chat: ${response.statusText}` });
			}
			
			// Reload chats after deletion
			return { success: true };
		} catch (error) {
			console.error('[+page.server.ts] Error deleting chat:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	getDocumentChunks: async ({ request, cookies }) => {
		const formData = await request.formData();
		const documentId = formData.get('documentId') as string;
		
		console.log('[+page.server.ts] Getting document chunks:', documentId);
		
		try {
			const response = await fetch(`http://backend:8000/api/v1/documents/${documentId}/chunks`, {
				headers: {}
			});
			
			if (!response.ok) {
				return fail(response.status, { error: `Failed to load document chunks: ${response.statusText}` });
			}
			
			const documentWithChunks = await response.json();
			console.log('[+page.server.ts] Got document chunks:', documentWithChunks);
			
			// Return as JSON string to avoid flattening
			return { documentWithChunksData: JSON.stringify(documentWithChunks) };
		} catch (error) {
			console.error('[+page.server.ts] Error loading document chunks:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	updateDocumentChunks: async ({ request, cookies }) => {
		const formData = await request.formData();
		const documentId = formData.get('documentId') as string;
		const title = formData.get('title') as string;
		const chunksJson = formData.get('chunks') as string;
		
		console.log('[+page.server.ts] Updating document chunks:', documentId);
		
		try {
			const chunks = JSON.parse(chunksJson);
			
			const response = await fetch(`http://backend:8000/api/v1/documents/${documentId}/chunks`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					title,
					chunks
				})
			});
			
			if (!response.ok) {
				const error = await response.text();
				console.error('[+page.server.ts] Update chunks failed:', error);
				return fail(response.status, { error: `Failed to update document: ${response.statusText}` });
			}
			
			const result = await response.json();
			console.log('[+page.server.ts] Update result:', result);
			
			// Return as JSON string to avoid flattening
			return { updateResult: JSON.stringify(result) };
		} catch (error) {
			console.error('[+page.server.ts] Error updating document chunks:', error);
			return fail(500, { error: 'Internal server error' });
		}
	},
	
	saveChatToKnowledge: async ({ request, cookies }) => {
		const formData = await request.formData();
		const chatId = formData.get('chatId') as string;
		const title = formData.get('title') as string | null;
		const content = formData.get('content') as string | null;
		const saveMode = formData.get('saveMode') as string | null;
		
		console.log('[+page.server.ts] Saving chat to knowledge:', chatId);
		
		try {
			let response;
			
			if (title && (content || saveMode === 'messages')) {
				// Save with custom content
				const body: any = {
					title,
					save_mode: saveMode || 'content'
				};
				
				if (content) {
					body.content = content;
				}
				
				response = await fetch(`http://backend:8000/api/v1/chats/${chatId}/save-to-knowledge`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify(body)
				});
			} else {
				// Simple save without custom content
				response = await fetch(`http://backend:8000/api/v1/chats/${chatId}/save-to-knowledge`, {
					method: 'POST',
					headers: {}
				});
			}
			
			if (!response.ok) {
				const error = await response.text();
				console.error('[+page.server.ts] Save to knowledge failed:', error);
				return fail(response.status, { error: `Failed to save to knowledge: ${response.statusText}` });
			}
			
			const result = await response.json();
			return { success: true, ...result };
		} catch (error) {
			console.error('[+page.server.ts] Error saving to knowledge:', error);
			return fail(500, { error: 'Internal server error' });
		}
	}
};
