#!/bin/bash
# Wizardry Development Setup Script
# Run this every time you work on the Wizardry repo

set -e  # Exit on any error

echo "🧙‍♂️ Setting up Wizardry development environment..."

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]] || [[ ! -d "wizardry" ]]; then
    echo "❌ Error: Run this script from the Wizardry repo root"
    exit 1
fi

# Check Python version
if ! python3 --version | grep -q "Python 3\.[8-9]\|Python 3\.1[0-9]"; then
    echo "❌ Error: Python 3.8+ required"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install wizardry in development mode
echo "🔧 Installing Wizardry in development mode..."
pip install -e .

# Verify installation
echo "✅ Verifying installation..."
if wizardry --help > /dev/null 2>&1; then
    echo "✅ Wizardry CLI installed successfully"
else
    echo "❌ Error: Wizardry CLI not working"
    exit 1
fi

# Run tests
echo "🧪 Running tests..."
python test_wizardry.py

echo ""
echo "🎉 Setup complete! Wizardry is ready for development."
echo ""
echo "📝 To stay in this environment, run:"
echo "   source venv/bin/activate"
echo ""
echo "🚀 To test Wizardry, run:"
echo "   ./test_example.sh"
echo ""
echo "💡 Available commands:"
echo "   wizardry --help"
echo "   wizardry setup --repo /path/to/test/repo"
echo "   wizardry status"
echo "   wizardry sessions"