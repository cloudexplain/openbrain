# Claude Instructions

## General Guidelines

### Production-Ready Code
- **NEVER add dummy values, test data, or placeholder configurations without explicit discussion with the user**
- **ALWAYS ask before adding default values that could leak into production** 
- Examples of what NOT to do without asking:
  - Adding dummy API keys or secrets
  - Using placeholder URLs or endpoints
  - Adding test/development-only defaults
  - Creating mock data that might persist
- If a required configuration is missing, explain the issue and ask how to properly handle it

### Debugging
- **NEVER remove debug statements (like `pdb.set_trace()`, `console.log()`, `print()` debugging, etc.) unless explicitly asked**
- Debug statements are intentionally placed and should be preserved during code modifications

## Project-Specific Information

### Chat to Document Conversion
- Chats can be saved as documents with `source_type = "chat"`
- The endpoint `/chats/{chat_id}/save-to-knowledge` handles this conversion
- Documents are chunked and embedded for semantic search