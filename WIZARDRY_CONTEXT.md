# Wizardry: Complete Context Documentation

This document provides comprehensive context about the Wizardry multi-agent workflow orchestrator for future AI development work.

## Executive Summary

Wizardry is a CLI tool that automates code implementation and review workflows using Claude Code SDK. It orchestrates two specialized AI agents (implementer → reviewer) that collaborate to implement features, fix bugs, and create pull requests autonomously.

### Key Value Proposition
- **Fully Automated**: No manual Claude Code interaction required
- **Isolated Workspaces**: Each workflow runs on separate git branches  
- **Session Management**: Multiple concurrent workflows on same repo
- **Complete Audit Trail**: Full transcript logging for debugging
- **GitHub Integration**: Automatic PR creation when approved

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │    │   Orchestrator   │    │   Git Repo      │
│   (CLI Command) │───▶│   (SDK Client)   │───▶│   (Isolated     │
│                 │    │                  │    │    Branch)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Agent Chain    │
                    │                  │
                    │ 1. Implementer   │──┐
                    │    Agent         │  │
                    │                  │  │
                    │ 2. Reviewer      │◀─┘
                    │    Agent         │
                    │                  │
                    │ 3. PR Creation   │
                    └──────────────────┘
```

## Core Components

### 1. CLI Interface (`wizardry/cli/__init__.py`)

**Purpose**: Main user interface for all Wizardry operations

**Key Commands**:
- `wizardry run --repo X --branch Y --task Z` - Execute workflow
- `wizardry setup --repo X` - Initialize repo for Wizardry  
- `wizardry sessions` - List active workflows
- `wizardry transcripts <id>` - View agent conversations
- `wizardry kill <id>` - Terminate workflow

### 2. Orchestrator Engine (`wizardry/orchestrator.py`)

**Purpose**: Core coordination logic using Claude Code SDK

**Critical Configuration**:
```python
options = ClaudeCodeOptions(
    system_prompt=self.implementer_prompt,
    max_turns=10,
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "LS", "MultiEdit"],
    model="claude-3-5-sonnet-20241022",
    cwd=str(self.repo_path),           # CRITICAL: Set working directory
    permission_mode="acceptEdits"       # CRITICAL: Auto-accept file operations
)
```

**Key Methods**:
- `_run_implementer()` - Spawns implementer agent session
- `_run_reviewer()` - Spawns reviewer agent with diff analysis
- `_create_pr()` - Creates GitHub PR using `gh` CLI
- `_create_isolated_workspace()` - Creates git branch isolation

### 3. Session Management

**Registry Location**: `/tmp/wizardry-sessions/registry.json`

**Session Structure**:
```json
{
  "workflow-123456-abc123": {
    "session_id": "workflow-123456-abc123",
    "repo_path": "/path/to/repo", 
    "base_branch": "main",
    "task": "Implement user authentication",
    "status": "in_progress",
    "created_at": "2024-01-01T12:00:00",
    "workspace_path": "/tmp/wizardry-sessions/workflow-123456-abc123"
  }
}
```

**Transcript Location**: `/tmp/wizardry-sessions/{workflow-id}/transcripts/`
- `implementer.md` - Full implementer conversation
- `reviewer.md` - Full reviewer conversation

### 4. Agent Configurations

#### Implementer Agent Prompt
**Role**: Analyze tasks and implement clean, minimal solutions

**Key Instructions**:
- **MUST actually write code and commit it** (critical emphasis)
- Follow existing codebase patterns exactly
- Make minimal invasive changes
- Include structured JSON output for handoff

**Output Format**:
```json
{
  "rationale": "Brief explanation of approach",
  "files_modified": ["list of changed files"],
  "confidence": 8,
  "testing_notes": "How solution was verified",
  "ready_for_review": true
}
```

#### Reviewer Agent Prompt  
**Role**: Critically review implementations for quality and correctness

**Review Criteria**: Readability, maintainability, consistency, simplicity, security

**Output Format**:
```json
{
  "approval": false,
  "overall_assessment": "Summary of code quality",
  "strengths": ["Positive aspects"],
  "concerns": ["Issues to address"],
  "suggested_fixes": ["Concrete improvements"],
  "confidence": 8
}
```

## Workflow Sequence

1. **Initialization**:
   - User runs `wizardry run --repo X --branch Y --task Z`
   - Validates repo exists and has `.git`
   - Creates unique workflow ID: `workflow-{timestamp}-{random}`

2. **Workspace Setup**:
   - Creates isolated branch: `wizardry-{workflow-id}`
   - Registers session in `/tmp/wizardry-sessions/registry.json`
   - Creates transcript directories

3. **Implementer Phase**:
   - Spawns Claude Code SDK session with implementer prompt
   - Agent analyzes codebase and implements solution
   - **CRITICAL**: Must actually commit code with `git add . && git commit`
   - Returns structured JSON with implementation details

4. **Reviewer Phase**:  
   - Extracts git diff between base branch and implementation branch
   - Spawns reviewer agent with diff and implementation context
   - Reviews for quality, correctness, and consistency
   - Returns approval/rejection with detailed feedback

5. **Iteration Management**:
   - If approved → Create PR and complete workflow
   - If rejected → Could re-run implementer (max 2 iterations)
   - Update session status in registry

6. **PR Creation**:
   - Uses `gh` CLI to create pull request
   - Includes workflow metadata and transcript links
   - Returns PR URL for user

## Technical Requirements

### Dependencies (`requirements.txt`)
```
rich>=13.0.0           # CLI formatting
typer>=0.9.0           # CLI framework  
python-dotenv>=1.0.0   # Environment variables
gitpython>=3.1.0       # Git operations
pydantic>=2.0.0        # Data validation
click>=8.0.0           # CLI commands
```

**External Dependencies**:
- `claude-code-sdk` - Claude Code SDK for Python
- `gh` CLI - GitHub PR creation (must be installed separately)

### Installation Process
```bash
# 1. Setup Python environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies  
pip install -r requirements.txt
pip install claude-code-sdk

# 3. Install Wizardry in development mode
pip install -e .

# 4. Install GitHub CLI
brew install gh  # or appropriate package manager

# 5. Verify installation
wizardry --help
```

## Historical Context: Evolution & Pivots

### Phase 1: Slash Commands Approach (Failed)
- Initially tried custom slash commands in `.claude/commands/workflow.md`
- **Issue**: Slash commands are prompt templates, not executable scripts
- **Lesson**: Claude Code slash commands cannot execute bash or spawn agents

### Phase 2: Hooks Approach (Attempted)
- Tried using `.claude/hooks/` for agent coordination  
- **Issue**: Hooks are for tool interception, not agent orchestration
- **Lesson**: Hooks cannot spawn new Claude Code sessions

### Phase 3: SDK Approach (Success)
- Pivoted to Claude Code SDK with programmatic control
- **Key Insight**: `permission_mode="acceptEdits"` required for file operations
- **Key Insight**: `cwd=str(repo_path)` required for correct working directory
- **Success**: Full workflow automation achieved

## Critical Fixes Applied

### Issue: Implementer Not Writing Files
**Symptoms**: Empty git diffs, reviewer seeing no changes
**Root Causes**:
1. Missing `permission_mode="acceptEdits"` in SDK options
2. Incorrect working directory (`cwd` not set)  
3. Prompt insufficiently emphasized code commitment requirement

**Solutions**:
1. Added `permission_mode="acceptEdits"` to all SDK options
2. Set `cwd=str(self.repo_path)` for all sessions
3. Enhanced prompts with **CRITICAL** emphasis on committing code

### Issue: PR Creation Failed
**Symptoms**: `[Errno 2] No such file or directory: 'gh'`
**Solution**: User must install GitHub CLI separately: `brew install gh`

## Extension Points for UX Improvements

### 1. Web UI Dashboard
**Current State**: CLI-only interface
**Opportunity**: Build web dashboard reading session registry
**Implementation**: 
- Flask/FastAPI server reading `/tmp/wizardry-sessions/registry.json`
- Real-time session monitoring via WebSocket
- Transcript viewer with syntax highlighting
- Workflow status visualization

### 2. IDE Integration  
**Current State**: Standalone CLI tool
**Opportunity**: VS Code / JetBrains plugins
**Implementation**:
- Plugin calls `wizardry run` API
- Inline diff preview of agent changes
- One-click workflow initiation from editor

### 3. Enhanced Session Management
**Current State**: Basic registry in `/tmp/`
**Opportunity**: Database storage with rich metadata
**Implementation**:
- SQLite/PostgreSQL for persistence  
- Workflow templates and presets
- Performance analytics and success rates

### 4. Advanced Agent Configuration
**Current State**: Hard-coded prompts in orchestrator  
**Opportunity**: Configurable agent personalities
**Implementation**:
- YAML/JSON agent config files
- Custom tool restrictions per agent
- Dynamic prompt templating

### 5. Multi-Repository Workflows
**Current State**: Single repo per workflow
**Opportunity**: Cross-repo dependency management
**Implementation**:
- Workflow graphs spanning multiple repos
- Dependency-aware execution ordering
- Monorepo support with workspace isolation

## File Structure Summary

```
wizardry/
├── __init__.py                 # Package initialization
├── __main__.py                 # Entry point for `python -m wizardry`
├── cli/
│   └── __init__.py             # CLI commands and interface
├── orchestrator.py             # Core SDK-based orchestration logic
├── templates/                  # Empty (legacy from slash command approach)
└── hooks/                      # Empty (legacy from hooks approach)

# Root files
├── setup.py                    # Package definition and entry points  
├── requirements.txt            # Python dependencies
├── setup.sh                    # Development environment setup
├── test_wizardry.py           # Test suite for template validation
├── README.md                   # User-facing documentation
└── USAGE_EXAMPLE.md           # Example usage scenarios
```

## Usage Examples

### Basic Workflow
```bash
# Setup repository
cd /path/to/your/repo
wizardry setup --repo .

# Run workflow  
wizardry run --repo . --branch main --task "Add user authentication system"

# Monitor progress
wizardry sessions
wizardry transcripts workflow-123456-abc123
```

### Advanced Scenarios
```bash
# Multiple concurrent workflows
wizardry run --repo /repo1 --branch main --task "Fix login bug" &
wizardry run --repo /repo1 --branch develop --task "Add email validation" &

# Cleanup
wizardry kill workflow-123456-abc123
```

## Troubleshooting Guide

### Common Issues

1. **"No module named 'claude_code_sdk'"**
   - Solution: `pip install claude-code-sdk`

2. **"Implementer not committing code"**  
   - Check `permission_mode="acceptEdits"` in orchestrator
   - Verify `cwd` is set correctly
   - Review implementer prompt emphasizes committing

3. **"gh: command not found"**
   - Solution: `brew install gh` or appropriate package manager

4. **"Repository not setup for Wizardry"**
   - Solution: `wizardry setup --repo /path/to/repo`

5. **Sessions not showing up**
   - Check `/tmp/wizardry-sessions/registry.json` exists
   - Verify write permissions to `/tmp/`

## Performance Characteristics

**Typical Execution Times**:
- Simple bug fix: 2-5 minutes
- Feature implementation: 5-15 minutes  
- Complex refactoring: 15-30 minutes

**Resource Usage**:
- Memory: ~100MB per active session
- Disk: ~10MB per session (transcripts)
- Network: Depends on Claude API usage

**Scaling Limits**:
- Concurrent sessions: Limited by system resources and API rate limits
- Repository size: No inherent limits (depends on git operations)
- Task complexity: Limited by agent context windows

## Future Roadmap Ideas

### Short Term (1-3 months)
- [ ] Web dashboard for session monitoring
- [ ] Improved error handling and recovery
- [ ] Agent prompt customization via config files
- [ ] Workflow templates for common tasks

### Medium Term (3-6 months)  
- [ ] IDE plugin for VS Code
- [ ] Advanced session analytics and reporting
- [ ] Multi-step workflow support (more than 2 agents)
- [ ] Integration with CI/CD pipelines

### Long Term (6+ months)
- [ ] Multi-repository workflow orchestration  
- [ ] Custom agent training on codebase patterns
- [ ] Workflow marketplace and sharing
- [ ] Enterprise features (SSO, audit logs, compliance)

## Conclusion

Wizardry successfully demonstrates automated code implementation using multi-agent coordination with Claude Code SDK. The current implementation provides a solid foundation for building more sophisticated workflow automation tools.

The key technical breakthrough was using `permission_mode="acceptEdits"` with proper `cwd` configuration to enable autonomous code writing. This pattern can be extended to support more complex agent interactions and workflow scenarios.

For AI developers working on UX improvements: focus on the session management system (`/tmp/wizardry-sessions/`) and the structured agent outputs (JSON blocks) as the primary integration points for building richer interfaces.

---

**Last Updated**: 2025-01-09  
**Version**: 1.0.0  
**Context**: Complete implementation with successful test workflows