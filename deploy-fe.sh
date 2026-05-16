#!/bin/bash

# Deployment script for Apex Trading Bot Frontend
echo "🚀 Starting frontend deployment..."
docker compose -f docker-compose.prod.yml up -d --build frontend
echo "✅ Frontend deployment complete!"
