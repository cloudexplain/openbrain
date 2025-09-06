// Direct Docker network communication
const API_BASE_URL = 'http://backend:8000/api/v1';
console.log('[API Config] Using API URL:', API_BASE_URL);

export interface Message {
	id: string;
	content: string;
	role: 'user' | 'assistant';
	timestamp: Date;
	chat_id: string;
	token_count?: number;
}

export interface Chat {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
	messages: Message[];
}

export interface ChatListItem {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
	last_message?: string;
	message_count: number;
}

export interface ChunkUsed {
	chunk_id: string;
	chunk_index: number;
	page_number?: number;
	page_index?: number;
	text_position?: {
		start?: number;
		end?: number;
	};
	similarity: number;
	content_preview: string;
}

export interface DocumentReference {
	id: string;
	title: string;
	source_type: string;
	chunk_count: number;
	max_similarity: number;
	avg_similarity: number;
	chunks_used?: ChunkUsed[];
	tags: any[];
}

export interface StreamResponse {
	type: 'content' | 'done' | 'error';
	content?: string;
	message_id?: string;
	chat_id?: string;
	error?: string;
	document_references?: DocumentReference[];
}

export interface Document {
	id: string;
	title: string;
	source_type: string;
	source_id?: string;
	filename?: string;
	file_type?: string;
	created_at: string;
	updated_at: string;
	chunk_count: number;
	metadata: Record<string, any>;
}

export interface DocumentDetail extends Document {
	content: string;
}

export interface DocumentChunk {
	id: string;
	content: string;
	chunk_index: number;
	token_count: number;
	summary?: string;
	metadata?: Record<string, any>;
}

export interface DocumentWithChunks extends Document {
	chunks: DocumentChunk[];
}

class ApiClient {
	private baseUrl: string;

	constructor(baseUrl: string = API_BASE_URL) {
		this.baseUrl = baseUrl;
	}

	private async request(endpoint: string, options: RequestInit = {}): Promise<Response> {
		console.log('[API Client] Preparing request...', this.baseUrl);
		const url = `${this.baseUrl}${endpoint}`;
		const timestamp = new Date().toISOString();
		
		console.log(`[API Request @ ${timestamp}]`);
		console.log(`[API Request] Method: ${options.method || 'GET'}`);
		console.log(`[API Request] Full URL: ${url}`);
		console.log(`[API Request] Base URL: ${this.baseUrl}`);
		console.log(`[API Request] Endpoint: ${endpoint}`);
		console.log('[API Request] Headers:', {
			'Content-Type': 'application/json',
			...options.headers
		});
		if (options.body) {
			try {
				const parsedBody = JSON.parse(options.body as string);
				console.log('[API Request] Body (parsed):', parsedBody);
			} catch {
				console.log('[API Request] Body (raw):', options.body);
			}
		}
		
		try {
			console.log('[API Request] Initiating fetch...', url);
			const response = await fetch(url, {
				headers: {
					'Content-Type': 'application/json',
					...options.headers
				},
				...options
			});
			
			console.log('[API Response] Received response');
			console.log('[API Response] Status:', response.status, response.statusText);
			console.log('[API Response] OK:', response.ok);
			console.log('[API Response] URL:', response.url);
			console.log('[API Response] Type:', response.type);
			console.log('[API Response] Headers:', Array.from(response.headers.entries()));
			
			if (!response.ok) {
				console.error('[API Error] Response not OK');
				console.error('[API Error] Status:', response.status);
				console.error('[API Error] StatusText:', response.statusText);
				console.error('[API Error] URL:', url);
				
				// Try to get error body
				try {
					const errorBody = await response.text();
					console.error('[API Error] Response body:', errorBody);
				} catch (e) {
					console.error('[API Error] Could not read error body:', e);
				}
				
				throw new Error(`API request failed: ${response.status} ${response.statusText}`);
			}
			
			console.log('[API Response] Success!');
			return response;
		} catch (error) {
			console.error('[API Error] Fetch failed');
			console.error('[API Error] Error:', error);
			console.error('[API Error] Error type:', error.constructor.name);
			console.error('[API Error] Error message:', error.message);
			console.error('[API Error] Error stack:', error.stack);
			console.error('[API Error] Failed URL:', url);
			throw error;
		}
	}

	async getChats(): Promise<ChatListItem[]> {
		const timestamp = new Date().toISOString();
		console.log(`[getChats @ ${timestamp}] Starting request to fetch chats`);
		console.log('[getChats] Base URL:', this.baseUrl);
		console.log('[getChats] Endpoint: /chats');
		
		try {
			const response = await this.request('/chats');
			const chats = await response.json();
			console.log('[getChats] Successfully received chats');
			console.log('[getChats] Number of chats:', chats.length);
			console.log('[getChats] Chats data:', JSON.stringify(chats, null, 2));
			
			return chats.map((chat: any) => ({
				...chat,
				timestamp: new Date(chat.updated_at)
			}));
		} catch (error) {
			console.error('[getChats] ERROR: Failed to fetch chats');
			console.error('[getChats] Error:', error);
			console.error('[getChats] Error type:', error.constructor.name);
			console.error('[getChats] Error message:', error.message);
			throw error;
		}
	}

	async getChat(chatId: string): Promise<Chat> {
		console.log("Calling chats/{chatId}")
		const response = await this.request(`/chats/${chatId}`);
		const chat = await response.json();
		
		return {
			...chat,
			messages: chat.messages.map((msg: any) => ({
				...msg,
				timestamp: new Date(msg.created_at)
			}))
		};
	}

	async createChat(title: string): Promise<Chat> {
		const response = await this.request('/chats', {
			method: 'POST',
			body: JSON.stringify({ title })
		});
		
		return await response.json();
	}

	async deleteChat(chatId: string): Promise<void> {
		await this.request(`/chats/${chatId}`, {
			method: 'DELETE'
		});
	}

	async saveChatToKnowledge(chatId: string): Promise<{message: string, chunks_created: number, document_id: string}> {
		const response = await this.request(`/chats/${chatId}/save-to-knowledge`, {
			method: 'POST'
		});
		return await response.json();
	}

	async saveChatToKnowledgeWithContent(
		chatId: string, 
		title: string, 
		content: string
	): Promise<{message: string, chunks_created: number, document_id: string}> {
		const response = await this.request(`/chats/${chatId}/save-to-knowledge-edited`, {
			method: 'POST',
			body: JSON.stringify({ 
				title, 
				content,
				mode: 'document'
			})
		});
		return await response.json();
	}

	async saveChatToKnowledgeWithMessages(
		chatId: string, 
		title: string, 
		messages: Array<{role: string, content: string}>
	): Promise<{message: string, chunks_created: number, document_id: string}> {
		const response = await this.request(`/chats/${chatId}/save-to-knowledge-edited`, {
			method: 'POST',
			body: JSON.stringify({ 
				title, 
				messages,
				mode: 'messages'
			})
		});
		return await response.json();
	}

	async searchKnowledge(
		query: string,
		limit: number = 5,
		similarity_threshold: number = 0.7,
		source_types?: string[]
	): Promise<{
		query: string,
		results: Array<{
			id: string,
			content: string,
			chunk_index: number,
			token_count: number,
			summary?: string,
			distance: number,
			document: {
				id: string,
				title: string,
				source_type: string,
				source_id: string
			},
			metadata: any,
			created_at: string
		}>,
		total_results: number
	}> {
		const body: any = {
			query,
			limit,
			similarity_threshold
		};
		
		if (source_types) {
			body.source_types = source_types;
		}
		
		const response = await this.request('/search', {
			method: 'POST',
			body: JSON.stringify(body)
		});
		return await response.json();
	}

	async getDocuments(): Promise<Document[]> {
		const response = await this.request('/documents');
		return await response.json();
	}

	async getDocument(documentId: string): Promise<DocumentDetail> {
		const response = await this.request(`/documents/${documentId}`);
		return await response.json();
	}

	async getDocumentWithChunks(documentId: string): Promise<DocumentWithChunks> {
		const response = await this.request(`/documents/${documentId}/chunks`);
		return await response.json();
	}

	async updateDocumentChunks(
		documentId: string, 
		title: string,
		chunks: DocumentChunk[]
	): Promise<{message: string, updated_chunks: string[], document_id: string}> {
		const response = await this.request(`/documents/${documentId}/chunks`, {
			method: 'PUT',
			body: JSON.stringify({
				title: title,
				chunks: chunks
			})
		});
		return await response.json();
	}

	async uploadDocument(file: File): Promise<{message: string, upload_id: string, status: string}> {
		const url = `${this.baseUrl}/documents/upload`;
		const timestamp = new Date().toISOString();
		
		console.log(`[uploadDocument @ ${timestamp}] Starting file upload`);
		console.log('[uploadDocument] URL:', url);
		console.log('[uploadDocument] File name:', file.name);
		console.log('[uploadDocument] File size:', file.size, 'bytes');
		console.log('[uploadDocument] File type:', file.type);
		
		const formData = new FormData();
		formData.append('file', file);
		
		try {
			console.log('[uploadDocument] Initiating upload...');
			const response = await fetch(url, {
				method: 'POST',
				body: formData
			});
			
			console.log('[uploadDocument] Response received');
			console.log('[uploadDocument] Status:', response.status, response.statusText);
			console.log('[uploadDocument] Response OK:', response.ok);
			console.log('[uploadDocument] Response headers:', Array.from(response.headers.entries()));
			
			if (!response.ok) {
				console.error('[uploadDocument] ERROR: Upload failed');
				console.error('[uploadDocument] Status:', response.status);
				console.error('[uploadDocument] StatusText:', response.statusText);
				
				// Try to get error body
				try {
					const errorBody = await response.text();
					console.error('[uploadDocument] Error response body:', errorBody);
				} catch (e) {
					console.error('[uploadDocument] Could not read error body:', e);
				}
				
				throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
			}
			
			const result = await response.json();
			console.log('[uploadDocument] SUCCESS: Upload completed');
			console.log('[uploadDocument] Result:', result);
			return result;
		} catch (error) {
			console.error('[uploadDocument] EXCEPTION CAUGHT');
			console.error('[uploadDocument] Error:', error);
			console.error('[uploadDocument] Error type:', error.constructor.name);
			console.error('[uploadDocument] Error message:', error.message);
			throw error;
		}
	}

	async sendMessage(message: string, chatId?: string): Promise<ReadableStream<StreamResponse>> {
		const endpoint = '/chat';
		const url = `${this.baseUrl}${endpoint}`;
		const payload = {
			message,
			chat_id: chatId || null
		};
		const timestamp = new Date().toISOString();
		
		console.log(`[sendMessage @ ${timestamp}] ========== START ==========`);
		console.log('[sendMessage] Base URL:', this.baseUrl);
		console.log('[sendMessage] Endpoint:', endpoint);
		console.log('[sendMessage] Full URL:', url);
		console.log('[sendMessage] Message:', message);
		console.log('[sendMessage] Chat ID:', chatId || 'null');
		console.log('[sendMessage] Payload:', JSON.stringify(payload, null, 2));
		
		let response: Response;
		
		try {
			console.log('[sendMessage] Initiating fetch...');
			console.log('[sendMessage] Fetch options:', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			
			response = await fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(payload)
			});
			
			console.log('[sendMessage] Response received');
			console.log('[sendMessage] Status:', response.status, response.statusText);
			console.log('[sendMessage] Response OK:', response.ok);
			console.log('[sendMessage] Response URL:', response.url);
			console.log('[sendMessage] Response type:', response.type);
			console.log('[sendMessage] Response headers:', Array.from(response.headers.entries()));
			
			if (!response.ok) {
				console.error('[sendMessage] ERROR: Request failed');
				console.error('[sendMessage] Status code:', response.status);
				console.error('[sendMessage] Status text:', response.statusText);
				console.error('[sendMessage] Failed URL:', url);
				
				// Try to read error body
				try {
					const errorText = await response.text();
					console.error('[sendMessage] Error response body:', errorText);
				} catch (e) {
					console.error('[sendMessage] Could not read error body:', e);
				}
				
				throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
			}
			
			if (!response.body) {
				console.error('[sendMessage] ERROR: No response body received');
				throw new Error('No response body received');
			}
			
			console.log('[sendMessage] SUCCESS: Got response body, creating stream');
			console.log(`[sendMessage @ ${timestamp}] ========== END ==========`);
		} catch (error) {
			console.error('[sendMessage] EXCEPTION CAUGHT');
			console.error('[sendMessage] Error:', error);
			console.error('[sendMessage] Error type:', error.constructor.name);
			console.error('[sendMessage] Error message:', error.message);
			console.error('[sendMessage] Error stack:', error.stack);
			console.error('[sendMessage] Failed URL:', url);
			console.error(`[sendMessage @ ${timestamp}] ========== ERROR END ==========`);
			throw error;
		}

		// Create a readable stream that parses SSE data
		const reader = response.body.getReader();
		const decoder = new TextDecoder();

		return new ReadableStream<StreamResponse>({
			start(controller) {
				let buffer = '';

				function pump(): Promise<void> {
					return reader.read().then(({ done, value }) => {
						if (done) {
							controller.close();
							return;
						}

						buffer += decoder.decode(value, { stream: true });
						const lines = buffer.split('\n');
						buffer = lines.pop() || '';

						for (const line of lines) {
							if (line.startsWith('data: ')) {
								try {
									const data = JSON.parse(line.slice(6));
									controller.enqueue(data);
								} catch (error) {
									console.error('Error parsing SSE data:', error);
								}
							}
						}

						return pump();
					}).catch((error) => {
						controller.error(error);
					});
				}

				return pump();
			}
		});
	}
}

export const apiClient = new ApiClient();
