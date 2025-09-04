#!/bin/bash
# Hook: Log user prompts and responses for transcript debugging

# Get workflow context
WORKFLOW_FILE=".wizardry/current_workflow.json"
if [[ ! -f "$WORKFLOW_FILE" ]]; then
  exit 0  # Not in a workflow, skip logging
fi

WORKFLOW_ID=$(cat "$WORKFLOW_FILE" | python3 -c "import json,sys; print(json.load(sys.stdin)['workflow_id'])")
TIMESTAMP=$(date -Iseconds)

# Create transcript directory
TRANSCRIPT_DIR="/tmp/wizardry-sessions/$WORKFLOW_ID/transcripts"
mkdir -p "$TRANSCRIPT_DIR"

# Log the prompt
echo "## [$TIMESTAMP] User Prompt" >> "$TRANSCRIPT_DIR/main.md"
echo "$1" >> "$TRANSCRIPT_DIR/main.md" 
echo "" >> "$TRANSCRIPT_DIR/main.md"