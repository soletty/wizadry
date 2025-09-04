# Wizardry: Multi-Agent Workflow Orchestrator

Automate code review workflows using Claude Code sub-agents with structured handoffs between implementer and reviewer agents.

## Quick Start

### Option 1: Modern Web UI (Recommended) ✨ NEW!
```bash
# Setup (first time only)
./wizardry/ui/setup.sh

# Launch the web interface
wizardry ui

# Open browser to http://localhost:3000
# Beautiful TypeScript/Next.js interface for managing workflows
```

### Option 2: Command Line
```bash
# Install
pip install -e .

# Setup a repository for workflows
wizardry setup --repo /path/to/your/repo

# Start workflow directly from CLI
wizardry run --repo /path/to/your/repo --branch main --task "Fix email validation bug"
```

### Option 3: Classic Claude Code (Legacy)
```bash
# Setup a repository for workflows
wizardry setup --repo /path/to/your/repo

# Start workflow
cd /path/to/your/repo
claude
/workflow --branch main --task "Fix email validation bug"
```

## How It Works

1. **Setup Phase**: Inject Claude Code configs into your repo
2. **Workflow Execution**: Custom slash command triggers agent workflow
3. **Automatic Coordination**: Hooks manage handoffs between implementer → reviewer
4. **PR Creation**: Automatically creates PR when review is approved

## Architecture

- **Sub-Agents**: Specialized implementer and reviewer with baked-in best practices
- **Hooks**: Automate agent coordination and workflow state management
- **Worktrees**: Multiple concurrent workflows via git worktree isolation
- **Transcripts**: Full conversation logging for debugging and analysis

## Commands

### Web UI
- `wizardry ui` - Launch the modern TypeScript/Next.js web interface (recommended)
- `wizardry ui --port 3001 --api-port 8001` - Launch on custom ports

### CLI Commands
- `wizardry setup --repo <path>` - Enable a repo for workflows
- `wizardry run --repo <path> --branch <branch> --task "<task>"` - Run workflow directly
- `wizardry status` - Check repo setup and active workflows  
- `wizardry sessions` - List all active sessions
- `wizardry transcripts <session-id>` - View session logs
- `wizardry kill <session-id>` - Terminate a workflow

## Workflow Commands (in Claude Code)

- `/workflow --branch <branch> --task "<description>"` - Start agent workflow