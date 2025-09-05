#!/bin/bash
# Hook: Prepare for tool usage and handle workflow state

TOOL_NAME="$1"
TOOL_ARGS="$2"

# Get workflow context
WORKFLOW_FILE=".wizardry/current_workflow.json"
if [[ ! -f "$WORKFLOW_FILE" ]]; then
  exit 0  # Not in a workflow, skip
fi

WORKFLOW_ID=$(cat "$WORKFLOW_FILE" | python3 -c "import json,sys; print(json.load(sys.stdin)['workflow_id'])")

# Log tool preparation
TRANSCRIPT_DIR="/tmp/wizardry-sessions/$WORKFLOW_ID/transcripts"
mkdir -p "$TRANSCRIPT_DIR"
echo "## [$(date -Iseconds)] Pre-Tool: $TOOL_NAME" >> "$TRANSCRIPT_DIR/tools.md"
echo "Args: $TOOL_ARGS" >> "$TRANSCRIPT_DIR/tools.md"
echo "" >> "$TRANSCRIPT_DIR/tools.md"

# Handle specific tool preparations
case "$TOOL_NAME" in
  "Edit"|"Write"|"MultiEdit")
    # Ensure we're working in the right directory
    echo "💾 Preparing file operation: $TOOL_NAME"
    ;;
  "Bash")
    # Log bash commands for debugging
    if [[ "$TOOL_ARGS" == *"git commit"* ]]; then
      echo "📝 Git commit detected - will trigger reviewer after completion"
    fi
    ;;
esac