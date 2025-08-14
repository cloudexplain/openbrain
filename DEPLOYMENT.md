# SecondBrain Deployment Guide

## Development vs Production

This project includes separate configurations for development and production environments.

### Development Mode

Development mode uses `docker-compose.dev.yml` and includes:
- Volume mounts for hot-reloading
- Debug mode enabled
- Source code mounted into containers
- Direct file editing capability

**To run in development mode:**
```bash
./dev.sh
# or
docker-compose -f docker-compose.dev.yml up
```

### Production Mode

Production mode uses `docker-compose.prod.yml` and includes:
- Optimized Docker images
- No source code mounts (everything copied into image)
- Production builds of frontend
- Non-root users for security
- Environment variable configuration

**To run in production mode:**

1. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. Build and run:
```bash
./prod.sh
# or
docker-compose -f docker-compose.prod.yml up --build
```

## Key Differences

| Feature | Development | Production |
|---------|------------|------------|
| Docker Compose File | `docker-compose.dev.yml` | `docker-compose.prod.yml` |
| Source Code | Mounted as volumes | Copied into image |
| Hot Reload | Yes | No |
| Build Optimization | No | Yes |
| Security | Runs as root | Runs as non-root user |
| Frontend Build | Dev server | Production build |
| Backend Server | Development mode | Production mode |
| Uploads Directory | Local mount | Docker volume |

## Environment Variables

Production mode requires the following environment variables in `.env`:

- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password (use a strong password!)
- `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Your chat model deployment name
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME` - Your embedding model deployment name
- `AZURE_OPENAI_API_VERSION` - API version (e.g., 2023-05-15)

Optional:
- `BACKEND_PORT` - Backend port (default: 8000)
- `FRONTEND_PORT` - Frontend port (default: 3000)

## Azure Storage for Uploads

For production deployments on Azure, you can mount Azure Files as the uploads volume:

1. Create an Azure Storage Account and File Share
2. Mount the file share to your Docker host or Kubernetes cluster
3. Update the uploads volume in `docker-compose.prod.yml` to use the mounted path

Example for Azure Files mount:
```yaml
volumes:
  uploads:
    driver: azure_file
    driver_opts:
      share_name: secondbrain-uploads
      storage_account_name: ${AZURE_STORAGE_ACCOUNT}
```

## Building for Production

To build production images:

```bash
# Build backend
docker build -f backend/Dockerfile.prod -t secondbrain-backend:prod ./backend

# Build frontend
docker build -f frontend/Dockerfile.prod -t secondbrain-frontend:prod ./frontend
```

## Deployment Checklist

- [ ] Configure `.env` file with production values
- [ ] Use strong passwords for database
- [ ] Configure Azure OpenAI credentials
- [ ] Set up SSL/TLS (use reverse proxy like nginx)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up monitoring and logging
- [ ] Configure Azure Files or other persistent storage for uploads
- [ ] Review and adjust resource limits in docker-compose.prod.yml