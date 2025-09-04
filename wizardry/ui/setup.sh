#!/bin/bash

# Wizardry UI Setup Script
echo "🧙‍♂️ Setting up Wizardry TypeScript UI..."

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Project root: $PROJECT_ROOT"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd "$PROJECT_ROOT"
pip install fastapi uvicorn[standard] websockets

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd "$SCRIPT_DIR/frontend"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first:"
    echo "   https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js which includes npm:"
    echo "   https://nodejs.org/"
    exit 1
fi

# Install frontend dependencies
npm install

echo ""
echo "✅ Wizardry UI setup complete!"
echo ""
echo "🚀 To launch the UI:"
echo "   wizardry ui"
echo ""
echo "Or manually:"
echo "   cd $SCRIPT_DIR/backend && uvicorn main:app --reload &"
echo "   cd $SCRIPT_DIR/frontend && npm run dev"