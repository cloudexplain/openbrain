# User Management Implementation Guide

## Overview

This document explains the implementation of user management in the SecondBrain application. The implementation provides basic authentication with JWT tokens and ensures all user data (chats, documents, tags) is isolated per user.

## Architecture Overview

### Backend Changes

#### 1. Database Schema Updates

**New Table: `users`**
- `id` (UUID, Primary Key)
- `username` (String, Unique)
- `password_hash` (String, BCrypt hashed)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**Modified Tables:**
- `chats`: Added `user_id` foreign key
- `documents`: Added `user_id` foreign key  
- `tags`: Added `user_id` foreign key, changed name uniqueness to be per-user
- `messages`: Inherit user through chat relationship
- `document_chunks`: Inherit user through document relationship
- `document_tags`: Inherit user through document relationship

#### 2. Authentication System

**Security Components:**
- **Password Hashing**: BCrypt with PassLib
- **JWT Tokens**: Using python-jose with 7-day expiration
- **Dependencies**: FastAPI dependency injection for authentication

**Key Files:**
- `backend/app/core/security.py`: Password hashing and JWT utilities
- `backend/app/core/deps.py`: Authentication dependencies  
- `backend/app/schemas/auth.py`: Pydantic schemas for authentication
- `backend/app/api/auth.py`: Login and user info endpoints

#### 3. API Endpoint Updates

**All existing endpoints now:**
- Require authentication via JWT Bearer token
- Filter all queries by current user's ID
- Only return data belonging to authenticated user

**New Endpoints:**
- `POST /api/v1/auth/login`: User login
- `GET /api/v1/auth/me`: Get current user info

#### 4. Service Layer Updates

**ChatService Changes:**
- All methods accept `user_id` parameter
- Queries filtered by user ownership
- User context passed through RAG system

**EmbeddingService Changes:**
- Similarity search filtered by user
- Document processing assigns user ownership
- Vector search respects user boundaries

### Frontend Changes

#### 1. Authentication Store (`src/lib/stores/auth.ts`)

**Features:**
- Reactive Svelte store for auth state
- Token storage in localStorage
- Automatic token validation on app start
- Centralized auth service for all components

#### 2. Login Page (`src/routes/login/+page.svelte`)

**Features:**
- Clean, responsive login form
- Form validation and error handling
- Loading states and user feedback
- Automatic redirect after successful login

#### 3. Route Protection (`src/routes/+layout.svelte`)

**Features:**
- Automatic authentication check on app load
- Route guards redirecting unauthenticated users
- Public routes configuration

#### 4. API Integration

**All API calls now:**
- Include JWT Bearer token in Authorization header
- Handle authentication errors gracefully
- Provide user feedback for auth failures

## Setup and Installation

### 1. Install Dependencies

```bash
cd backend
pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4
```

### 2. Run Database Migration

```bash
cd backend
alembic upgrade head
```

### 3. Create Initial User

```bash
cd backend
python create_user.py --interactive
```

Or:

```bash
python create_user.py --username admin --password securepassword123
```

### 4. Set Environment Variables

Add to your `.env` file:
```
SECRET_KEY=your-super-secret-key-change-this-in-production
```

## API Documentation

### Authentication Endpoints

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "username": "admin",
  "created_at": "2025-08-24T12:00:00Z"
}
```

### Protected Endpoints

All existing endpoints (`/api/v1/chats`, `/api/v1/documents`, etc.) now require authentication:

```http
GET /api/v1/chats
Authorization: Bearer <token>
```

## Frontend Usage

### Authentication Service

```javascript
import { authService } from '$lib/stores/auth';

// Login
await authService.login(username, password);

// Logout
authService.logout();

// Get auth headers for API calls
const headers = authService.getAuthHeaders();
```

### Authentication Store

```javascript
import { authStore } from '$lib/stores/auth';

// Subscribe to auth state
$authStore.isAuthenticated
$authStore.user
$authStore.isLoading
```

## Security Considerations

### Token Security
- **Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)
- **Expiration**: 7-day token lifetime
- **Validation**: Automatic token validation on app start

### Password Security
- **Hashing**: BCrypt with automatic salt generation
- **Validation**: Minimum 6 character requirement (easily configurable)

### Data Isolation
- **Complete Separation**: Users can only access their own data
- **Database Level**: All queries filtered by user_id
- **API Level**: Authentication required for all data endpoints

## Testing the Implementation

### 1. Create Test Users
```bash
cd backend
python create_user.py --username testuser1 --password test123
python create_user.py --username testuser2 --password test456
```

### 2. Test Authentication Flow
1. Visit `/login` in your browser
2. Login with created credentials
3. Verify redirect to main application
4. Test logout functionality

### 3. Test Data Isolation
1. Login as `testuser1`
2. Create some chats and documents
3. Logout and login as `testuser2`  
4. Verify you can't see testuser1's data
5. Create different data as testuser2
6. Switch back to testuser1 and verify isolation

## Migration from Non-User System

If you have existing data in the system:

### 1. Handle Existing Data
The migration creates user_id columns as nullable initially. You'll need to either:
- Assign existing data to a default user
- Clear existing data for a fresh start

### 2. Update Migration (if needed)
```sql
-- Option 1: Create default user and assign all data
INSERT INTO users (id, username, password_hash, created_at) 
VALUES ('default-uuid', 'admin', 'hashed-password', NOW());

UPDATE chats SET user_id = 'default-uuid' WHERE user_id IS NULL;
UPDATE documents SET user_id = 'default-uuid' WHERE user_id IS NULL;  
UPDATE tags SET user_id = 'default-uuid' WHERE user_id IS NULL;

-- Option 2: Clear existing data (if acceptable)
DELETE FROM document_chunks;
DELETE FROM documents;
DELETE FROM messages;  
DELETE FROM chats;
DELETE FROM document_tags;
DELETE FROM tags;
```

## Troubleshooting

### Common Issues

#### 1. Authentication Failures
- Check SECRET_KEY is set in environment
- Verify JWT token format and expiration
- Check password hashing with create_user.py script

#### 2. Database Migration Issues
- Ensure PostgreSQL is running
- Check database connection string
- Run migration manually: `alembic upgrade head`

#### 3. Frontend Auth Issues
- Check browser localStorage for tokens
- Verify API endpoints are reachable
- Check browser network tab for auth headers

#### 4. CORS Issues
- Ensure CORS_ORIGINS includes your frontend URL
- Check that preflight requests include auth headers

### Debugging Tips

#### Backend Debugging
```python
# Add to main.py for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check auth dependency
from app.core.deps import get_current_user
# This will log authentication attempts
```

#### Frontend Debugging
```javascript
// Check auth state
console.log($authStore);

// Check stored tokens
console.log(localStorage.getItem('auth_token'));

// Check API headers
console.log(authService.getAuthHeaders());
```

## Future Enhancements

### Planned Features
- [ ] Role-based permissions (admin/user)
- [ ] User registration endpoint
- [ ] Password reset functionality
- [ ] Session management
- [ ] Multi-factor authentication
- [ ] User profile management

### Security Improvements
- [ ] HTTP-only cookie storage for tokens
- [ ] Token refresh mechanism
- [ ] Rate limiting on login attempts
- [ ] Account lockout after failed attempts
- [ ] Audit logging for user actions

### UI/UX Improvements
- [ ] Remember me functionality
- [ ] Better error messaging
- [ ] Loading states throughout app
- [ ] User dashboard/settings page

## Conclusion

The user management implementation provides a solid foundation for multi-user SecondBrain deployment. The system ensures complete data isolation while maintaining the existing functionality. The JWT-based authentication is stateless and scalable, making it suitable for both single-server and distributed deployments.

The implementation follows security best practices and provides a clean separation between authentication logic and business logic, making future enhancements straightforward to implement.