#!/bin/bash

# UDYOGSETU Development Server Startup

set -e

echo "🚀 Starting UDYOGSETU services..."

# Start Docker Compose
docker-compose up --build

echo "✅ Services started!"
