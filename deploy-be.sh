#!/bin/bash

# Deployment script for Apex Trading Bot Backend
echo "🚀 Starting backend deployment..."

# Rebuild and restart backend container
docker compose -f docker-compose.prod.yml up -d --build backend

# Wait a few seconds for DB to be ready and run migrations
echo "⏳ Waiting for backend to stabilize..."
sleep 5

echo "📂 Running database migrations..."
docker exec apex-backend alembic upgrade head

echo "✅ Backend deployment and migrations complete!"
