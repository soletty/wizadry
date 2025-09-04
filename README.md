# Wizardry: Multi-Agent Workflow Orchestrator

Automate code review workflows using Claude Code sub-agents with structured handoffs between implementer and reviewer agents.

## Quick Start

```bash
# Install
pip install -e .

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

- `wizardry setup --repo <path>` - Enable a repo for workflows
- `wizardry status` - Check repo setup and active workflows  
- `wizardry sessions` - List all active sessions
- `wizardry transcripts <session-id>` - View session logs
- `wizardry kill <session-id>` - Terminate a workflow

## Workflow Commands (in Claude Code)

- `/workflow --branch <branch> --task "<description>"` - Start agent workflow