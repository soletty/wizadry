#!/bin/bash
# Test Wizardry with a simple example

set -e

echo "🧙‍♂️ Testing Wizardry on a sample repository..."

# Ensure we're in venv
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Activating virtual environment..."
    source venv/bin/activate
fi

# Create a simple test repository
TEST_REPO="/tmp/wizardry-test-repo"
rm -rf "$TEST_REPO"
mkdir -p "$TEST_REPO"
cd "$TEST_REPO"

echo "📁 Creating test repository..."

# Initialize git repo
git init
git config user.name "Wizardry Test"
git config user.email "test@wizardry.local"

# Create a simple Python file with a "bug"
cat > hello.py << 'EOF'
def greet_user(name):
    # Bug: no input validation
    return f"Hello {name}!"

def main():
    user = input("Enter your name: ")
    print(greet_user(user))

if __name__ == "__main__":
    main()
EOF

# Initial commit
git add hello.py
git commit -m "Initial commit with greeting function"

echo "✅ Test repository created: $TEST_REPO"
echo ""

# Setup Wizardry
echo "🔧 Setting up Wizardry in test repo..."
wizardry setup --repo "$TEST_REPO"

echo ""
echo "✅ Wizardry setup complete!"
echo ""
echo "🚀 To test the workflow:"
echo "   cd $TEST_REPO"
echo "   claude"
echo ""
echo "   Then in Claude Code run:"
echo "   /workflow --branch main --task \"Add input validation to greet_user function\""
echo ""
echo "📋 Expected workflow:"
echo "   1. Implementer will add validation to greet_user()"
echo "   2. Reviewer will check the implementation"  
echo "   3. PR will be created automatically when approved"
echo ""
echo "📊 Monitor progress with:"
echo "   wizardry sessions    # List active workflows"
echo "   wizardry status      # Check current repo status"