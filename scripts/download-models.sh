#!/bin/bash

echo "🤖 Waiting for Ollama to be ready..."
until curl -f http://ollama:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama..."
    sleep 5
done

echo "📥 Downloading Ollama models..."

# Download LLM Model
echo "Downloading smollm2:135m..."
curl -X POST http://ollama:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "smollm2:135m"}' \
  --max-time 600

# Download Embedding Model  
echo "Downloading nomic-embed-text..."
curl -X POST http://ollama:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "nomic-embed-text"}' \
  --max-time 600

# Alternative smaller models for testing
echo "Downloading smaller test models..."
curl -X POST http://ollama:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "tinyllama"}' \
  --max-time 600

echo "✅ All models downloaded successfully!"

# Test models
echo "🧪 Testing models..."
curl -X POST http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "smollm2:135m", "prompt": "Hello world", "stream": false}' \
  --max-time 60

echo "🎉 Setup completed!"
