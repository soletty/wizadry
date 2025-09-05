---
description: "Start a multi-agent workflow with implementer and reviewer"  
argument-hint: "--branch <branch> --task <description>"
allowed-tools: ["Bash", "Write", "Read", "Edit", "TodoWrite"]
---

# Wizardry Multi-Agent Workflow

I'll start a multi-agent workflow with your arguments: $ARGUMENTS

First, let me validate the arguments and environment:

```bash
# Parse and validate arguments  
ARGS="$ARGUMENTS"
BRANCH=$(echo "$ARGS" | sed -n 's/.*--branch \([^ ]*\).*/\1/p')
TASK=$(echo "$ARGS" | sed 's/.*--task //')

# Validation
if [[ -z "$BRANCH" ]]; then
    echo "❌ Error: --branch is required"
    echo "Usage: /workflow --branch <branch> --task <description>"
    exit 1
fi

if [[ -z "$TASK" ]]; then
    echo "❌ Error: --task is required"
    echo "Usage: /workflow --branch <branch> --task <description>"
    exit 1
fi

# Check if branch exists
if ! git show-ref --verify --quiet refs/heads/$BRANCH && ! git show-ref --verify --quiet refs/remotes/origin/$BRANCH; then
    echo "❌ Error: Branch '$BRANCH' does not exist"
    echo "Available branches:"
    git branch -a
    exit 1
fi

# Check if working directory is clean
if ! git diff --quiet HEAD; then
    echo "⚠️ Warning: Working directory has uncommitted changes"
    echo "Consider committing or stashing your changes before running workflow"
    git status --porcelain
fi

WORKFLOW_ID="workflow-$(date +%s)-$(openssl rand -hex 3)"

echo "🚀 Starting Wizardry workflow: $WORKFLOW_ID"
echo "📋 Task: $TASK"  
echo "🌿 Base branch: $BRANCH"
echo "📂 Repository: $(pwd)"
```

```bash
# Create workflow directory and config
mkdir -p .wizardry
cat > .wizardry/current_workflow.json << EOF
{
  "workflow_id": "$WORKFLOW_ID",
  "task": "$TASK",
  "branch": "$BRANCH",
  "started_at": "$(date -Iseconds)",
  "status": "implementer_phase", 
  "iteration_count": 0
}
EOF
```

```bash
# Create isolated branch (keeps your current branch clean)
echo "🔄 Switching to base branch: $BRANCH"
git checkout $BRANCH

if git checkout -b "wizardry-$WORKFLOW_ID"; then
    echo "🌟 Created isolated branch: wizardry-$WORKFLOW_ID"
else
    echo "❌ Failed to create branch wizardry-$WORKFLOW_ID"
    echo "This branch may already exist. Cleaning up..."
    git branch -D "wizardry-$WORKFLOW_ID" 2>/dev/null || true
    git checkout -b "wizardry-$WORKFLOW_ID"
    echo "🌟 Created isolated branch: wizardry-$WORKFLOW_ID (after cleanup)"
fi
```

```bash
# Create transcript directory and register session for monitoring
mkdir -p "/tmp/wizardry-sessions/$WORKFLOW_ID/transcripts"
mkdir -p /tmp/wizardry-sessions

# Register session in global registry
python3 -c "
import json
from datetime import datetime
registry_file = '/tmp/wizardry-sessions/registry.json'
try:
    with open(registry_file, 'r') as f:
        registry = json.load(f)
except:
    registry = {}

workflow_id = '$WORKFLOW_ID'
registry[workflow_id] = {
    'session_id': workflow_id,
    'repo_path': '$(pwd)',
    'base_branch': '$BRANCH', 
    'task': '$TASK',
    'status': 'in_progress',
    'created_at': '$(date -Iseconds)',
    'workspace_path': '/tmp/wizardry-sessions/$WORKFLOW_ID'
}

with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)
print('📊 Session registered for monitoring')
"

echo "✅ Workflow session initialized: $WORKFLOW_ID"
```

Now I'll **automatically trigger the Implementer Agent**:

**🔧 IMPLEMENTER PHASE STARTING**

/agents implementer

**Task**: $TASK

Please implement this task by following these steps:
1. Analyze the existing codebase to understand patterns and architecture
2. Implement the requested functionality with minimal, clean changes
3. Test your implementation if testing infrastructure exists  
4. Commit your changes with: git add . && git commit -m "descriptive message"
5. Include the required JSON implementation output when done

Focus on making something that works following existing patterns rather than perfect architecture.