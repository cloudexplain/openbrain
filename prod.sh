#!/bin/bash
# Production startup script

# Check if backend .env file exists
if [ ! -f backend/.env ]; then
    echo "WARNING: backend/.env file not found!"
    echo "The backend needs Azure OpenAI credentials."
    echo "Please create backend/.env with your Azure OpenAI settings:"
    echo "  cd backend"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your Azure OpenAI credentials"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting SecondBrain in PRODUCTION mode..."
docker compose -f docker-compose.prod.yml up "$@"