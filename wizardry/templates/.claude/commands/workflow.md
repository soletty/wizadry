---
description: "Start a multi-agent workflow with implementer and reviewer"  
argument-hint: "--branch <branch> --task <description>"
allowed-tools: ["Bash", "Write", "Read", "Edit", "TodoWrite"]
---

# Wizardry Multi-Agent Workflow

I'll start a multi-agent workflow with your arguments: $ARGUMENTS

Let me set up the workflow session step by step:

```bash
# Parse arguments  
ARGS="$ARGUMENTS"
BRANCH=$(echo "$ARGS" | sed -n 's/.*--branch \([^ ]*\).*/\1/p')
TASK=$(echo "$ARGS" | sed 's/.*--task //')
WORKFLOW_ID="workflow-$(date +%s)-$(openssl rand -hex 3)"

echo "🚀 Starting Wizardry workflow: $WORKFLOW_ID"
echo "📋 Task: $TASK"  
echo "🌿 Base branch: $BRANCH"
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
git checkout -b "wizardry-$WORKFLOW_ID"
echo "🌟 Created isolated branch: wizardry-$WORKFLOW_ID"
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

I need you to implement a notification service system. Here's the complete task:

**Task**: $TASK

**Requirements**:
- Create a notification service class that can store errors by user ID
- Integrate with the existing user state manager and websocket system  
- When a frontend connection connects via websocket, send stored errors as notifications
- Clear errors from the notification center after sending
- Follow existing codebase patterns and architecture
- Make minimal, clean changes that fit the existing code style
- Include the required JSON implementation output when done

Please start by exploring the existing websocket and user management code to understand the architecture, then implement the notification service following those patterns.