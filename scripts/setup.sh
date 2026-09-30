#!/bin/bash

# UDYOGSETU Setup Script

set -e

echo "🚀 Setting up UDYOGSETU environment..."

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file from .env.example"
fi

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✓ Backend dependencies installed"
else
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

cd ..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    npm install
    echo "✓ Frontend dependencies installed"
else
    echo "✓ Frontend dependencies already installed"
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Configure your API keys in .env file"
echo "  2. Start services: docker-compose up --build"
echo "  3. Access frontend: http://localhost:3000"
echo "  4. Access API: http://localhost:8000"
echo "  5. API docs: http://localhost:8000/docs"
echo ""
