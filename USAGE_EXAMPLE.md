# Wizardry Usage Example

## Complete Workflow Example

Here's how to use Wizardry to automate a bug fix with implementer → reviewer workflow:

### 1. Install Wizardry
```bash
cd /path/to/wizardry
pip install -e .  # or use venv/pipx
```

### 2. Setup Your Repository
```bash
# Enable your repo for agent workflows
wizardry setup --repo /path/to/your/project
```

### 3. Start a Workflow
```bash
cd /path/to/your/project
claude  # Opens Claude Code

# In Claude Code, run:
/workflow --branch main --task "Fix email validation bug in user registration"
```

### 4. What Happens Automatically

1. **Implementer Agent** activates:
   - Analyzes the codebase
   - Identifies the email validation issue
   - Implements a minimal fix
   - Commits the changes
   - Outputs structured implementation report

2. **Review Trigger** (via hooks):
   - Detects implementer's git commit
   - Automatically switches to reviewer agent
   - Passes diff and implementation context

3. **Reviewer Agent** activates:
   - Analyzes the implementation diff
   - Reviews code quality, patterns, security
   - Provides structured feedback
   - Approves or requests changes

4. **Iteration Loop** (if needed):
   - If reviewer rejects: implementer addresses feedback
   - Max 2 iterations to prevent endless loops

5. **PR Creation** (when approved):
   - Automatically creates GitHub PR
   - Includes full transcript links
   - Ready for human final review

### 5. Monitor Progress
```bash
# Check active workflows across all repos
wizardry sessions

# View detailed transcripts  
wizardry transcripts workflow-1693123456-abc123

# Kill a stuck workflow
wizardry kill workflow-1693123456-abc123
```

## Multi-Session Support

Run multiple workflows simultaneously:
```bash
# Terminal 1
cd /repo1 && claude
/workflow --branch feature-a --task "Add user profiles"

# Terminal 2  
cd /repo2 && claude
/workflow --branch main --task "Fix payment processing"

# Terminal 3
cd /repo1 && claude  
/workflow --branch feature-b --task "Add dark mode"
```

Each workflow gets isolated git worktrees and separate transcript logging.

## Expected Output

```
🚀 Starting Wizardry workflow: workflow-1693123456-abc123
📋 Task: Fix email validation bug in user registration
🌿 Base branch: main

🔧 IMPLEMENTER PHASE STARTING
[Implementer analyzes codebase and implements solution]

✅ IMPLEMENTER PHASE COMPLETE
🔍 REVIEWER PHASE STARTING  
[Reviewer analyzes implementation and provides feedback]

✅ REVIEW APPROVED - WORKFLOW COMPLETE
🚀 Creating pull request...
✅ Pull request created successfully!
```

## Files Created in Target Repo

After setup, your repo gets:
```
your-repo/
├── .claude/
│   ├── agents/
│   │   ├── implementer.json    # Implementer agent config
│   │   └── reviewer.json       # Reviewer agent config
│   ├── settings.json           # Hooks configuration
│   ├── commands/
│   │   └── workflow            # Custom /workflow command
│   └── hooks/                  # Coordination automation
└── .wizardry/                  # Created during workflow
    └── current_workflow.json   # Session state
```

The workflow creates transcripts in `/tmp/wizardry-sessions/{workflow-id}/transcripts/` for debugging and analysis.