# Claude Instructions

## General Guidelines

### Debugging
- **NEVER remove debug statements (like `pdb.set_trace()`, `console.log()`, `print()` debugging, etc.) unless explicitly asked**
- Debug statements are intentionally placed and should be preserved during code modifications

### Svelte 5 Syntax
- **ALWAYS use Svelte 5 runes mode syntax for this project**
- Use `let { prop } = $props()` instead of `export let prop`
- Use `$state()` for reactive variables instead of `let`
- Use `$derived()` for computed values instead of `$:`
- Use `$effect()` for side effects instead of `$:`
- This project uses Svelte 5 runes mode exclusively

### Development Commands
- **NEVER run `npm run dev` or execute production Python files in this repo**
- Development server execution and Python file execution is the user's responsibility
- Only suggest or mention commands if explicitly asked

## Project-Specific Information

### Chat to Document Conversion
- Chats can be saved as documents with `source_type = "chat"`
- The endpoint `/chats/{chat_id}/save-to-knowledge` handles this conversion
- Documents are chunked and embedded for semantic search