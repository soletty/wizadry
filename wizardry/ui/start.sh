#!/bin/bash

# Wizardry UI Startup Script
# This script launches the Streamlit UI for Wizardry

set -e

echo "🧙‍♂️ Starting Wizardry UI..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Project root: $PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please run the setup script first:"
    echo "  cd $PROJECT_ROOT"
    echo "  ./setup.sh"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$PROJECT_ROOT/venv/bin/activate"

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import streamlit" 2>/dev/null || {
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
}

python -c "import claude_code_sdk" 2>/dev/null || {
    echo "❌ Claude Code SDK not found. Installing..."
    pip install claude-code-sdk
}

# Install Wizardry in development mode if needed
echo "🔧 Installing Wizardry in development mode..."
cd "$PROJECT_ROOT"
pip install -e . >/dev/null 2>&1 || echo "Warning: Could not install Wizardry in dev mode"

# Create sessions directory if it doesn't exist
echo "📁 Setting up session storage..."
mkdir -p /tmp/wizardry-sessions

# Start Streamlit
echo ""
echo "🚀 Launching Wizardry UI..."
echo "📱 Open your browser to http://localhost:8501"
echo "⌨️  Press Ctrl+C to stop the server"
echo ""

cd "$SCRIPT_DIR"
exec streamlit run app.py \
    --server.port 8501 \
    --server.address localhost \
    --server.headless false \
    --browser.gatherUsageStats false \
    --theme.base "light" \
    --theme.primaryColor "#1f77b4" \
    --theme.backgroundColor "#ffffff" \
    --theme.secondaryBackgroundColor "#f0f2f6"