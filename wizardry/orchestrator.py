"""Core orchestrator using Claude Code SDK to coordinate agent workflows."""

import asyncio
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile
import random
import string

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from git import Repo
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows using Claude Code SDK."""
    
    def __init__(self, repo_path: str, base_branch: str, task: str):
        self.original_repo_path = Path(repo_path).resolve()
        self.base_branch = base_branch
        self.task = task
        self.workflow_id = self._generate_workflow_id()
        
        # Session tracking
        self.session_dir = Path(f"/tmp/wizardry-sessions/{self.workflow_id}")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        (self.session_dir / "transcripts").mkdir(exist_ok=True)
        
        # Create workspace copy of the repo for Conductor isolation
        self.repo_path = self._setup_workspace_repo()
        self.repo = Repo(self.repo_path)
        
        # Agent configurations
        self.implementer_prompt = self._load_implementer_prompt()
        self.reviewer_prompt = self._load_reviewer_prompt()
        self.test_planner_prompt = self._load_test_planner_prompt()
        
    def _setup_workspace_repo(self) -> Path:
        """Create a workspace using git worktrees for isolation."""
        import subprocess
        
        # Check if we're running in a Conductor workspace
        current_cwd = Path.cwd()
        conductor_workspace = "/Users/solal/Documents/GitHub/wizadry/.conductor/"
        
        if str(current_cwd).startswith(conductor_workspace):
            # Running in Conductor - create isolated worktree
            workspace_repo = self.session_dir / "workspace_repo"
            worktree_branch = f"wizardry-{self.workflow_id}"
            
            # Ensure session directory exists before creating worktree
            self.session_dir.mkdir(parents=True, exist_ok=True)
            
            console.print(f"🔄 Setting up git worktree for {self.original_repo_path}")
            console.print(f"🔄 Target directory: {workspace_repo}")
            console.print(f"🔄 Branch: {worktree_branch}")
            
            # Check if branch already exists
            branch_exists = False
            try:
                result = subprocess.run([
                    "git", "-C", str(self.original_repo_path),
                    "show-ref", "--verify", f"refs/heads/{worktree_branch}"
                ], capture_output=True, text=True)
                branch_exists = (result.returncode == 0)
            except:
                branch_exists = False
                
            try:
                if branch_exists:
                    console.print(f"🔄 Using existing branch: {worktree_branch}")
                    # Branch exists, use it without -b
                    result = subprocess.run([
                        "git", "-C", str(self.original_repo_path),
                        "worktree", "add", str(workspace_repo), worktree_branch
                    ], check=True, capture_output=True, text=True)
                else:
                    console.print(f"🔄 Creating new branch: {worktree_branch}")
                    # Branch doesn't exist, create it with -b
                    result = subprocess.run([
                        "git", "-C", str(self.original_repo_path), 
                        "worktree", "add", "-b", worktree_branch, 
                        str(workspace_repo), self.base_branch
                    ], check=True, capture_output=True, text=True)
                
                # Verify the worktree was actually created
                if workspace_repo.exists():
                    console.print(f"✅ Git worktree created at {workspace_repo}")
                    console.print(f"🌿 Branch: {worktree_branch}")
                    return workspace_repo
                else:
                    console.print(f"❌ Worktree command succeeded but directory not found: {workspace_repo}")
                    return self._fallback_clone_method()
                
            except subprocess.CalledProcessError as e:
                console.print(f"❌ Worktree creation failed: {e.stderr}")
                console.print(f"❌ Command output: {e.stdout}")
                console.print(f"❌ Return code: {e.returncode}")
                # Last fallback: use clone method
                return self._fallback_clone_method()
        else:
            # Not in Conductor - use original path but still create worktree for isolation
            return self._setup_local_worktree()
    
    def _fallback_clone_method(self) -> Path:
        """Fallback to clone method if worktrees fail."""
        workspace_repo = self.session_dir / "workspace_repo"
        console.print("🔄 Falling back to clone method...")
        
        try:
            import subprocess
            result = subprocess.run([
                "git", "clone", str(self.original_repo_path), str(workspace_repo)
            ], check=True, capture_output=True, text=True)
            
            console.print(f"✅ Workspace repo cloned to {workspace_repo}")
            return workspace_repo
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Clone fallback failed: {e.stderr}")
            return self.original_repo_path
    
    def _setup_local_worktree(self) -> Path:
        """Setup worktree even when not in Conductor for isolation."""
        import subprocess
        
        workspace_repo = self.session_dir / "workspace_repo"
        worktree_branch = f"wizardry-{self.workflow_id}"
        
        # Check if branch already exists
        branch_exists = False
        try:
            result = subprocess.run([
                "git", "-C", str(self.original_repo_path),
                "show-ref", "--verify", f"refs/heads/{worktree_branch}"
            ], capture_output=True, text=True)
            branch_exists = (result.returncode == 0)
        except:
            branch_exists = False
            
        try:
            if branch_exists:
                console.print(f"🔄 Using existing branch: {worktree_branch}")
                result = subprocess.run([
                    "git", "-C", str(self.original_repo_path),
                    "worktree", "add", str(workspace_repo), worktree_branch
                ], check=True, capture_output=True, text=True)
            else:
                console.print(f"🔄 Creating new branch: {worktree_branch}")
                result = subprocess.run([
                    "git", "-C", str(self.original_repo_path),
                    "worktree", "add", "-b", worktree_branch,
                    str(workspace_repo), self.base_branch
                ], check=True, capture_output=True, text=True)
            
            console.print(f"✅ Local worktree created at {workspace_repo}")
            return workspace_repo
        except subprocess.CalledProcessError as e:
            console.print(f"⚠️ Worktree creation failed, using original repo: {e.stderr}")
            return self.original_repo_path
    
    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = str(int(time.time()))
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
        return f"workflow-{timestamp}-{random_suffix}"
    
    def _load_implementer_prompt(self) -> str:
        """Load implementer agent system prompt."""
        return """You are the Implementer agent in a multi-agent workflow. Your role is to analyze tasks and implement clean, minimal solutions.

# 🚫 FORBIDDEN BEHAVIOR - NEVER DO THIS 🚫
- NEVER claim functionality "already exists" without implementing new code
- NEVER return ready_for_review=true without committing actual file changes
- NEVER skip implementation because something "looks similar" in the codebase
- NEVER claim a task is "already done" without verification and testing

# ✅ REQUIRED BEHAVIOR - ALWAYS DO THIS ✅
- ALWAYS create or modify at least one file for the requested functionality
- ALWAYS test your implementation works as specified
- ALWAYS commit your changes before reporting completion
- ALWAYS provide proof your implementation meets the exact requirements

# Core Principles
- **Minimal Invasiveness**: Make the smallest, cleanest change necessary to solve the problem
- **PMF Mentality**: Prioritize making something that works over perfect architecture
- **Clean Code**: Write readable, maintainable code that follows existing patterns
- **No Assumptions**: Only use libraries/frameworks that already exist in the codebase
- **Follow Conventions**: Match existing code style, naming, and patterns exactly

# YOUR MANDATORY PROCESS (EVERY STEP REQUIRED)

## Phase 1: Implementation  
1. Analyze the task and understand the existing codebase
2. Identify what SPECIFIC functionality is requested
3. **ACTUALLY IMPLEMENT** - use Write/Edit tools to create/modify files
4. **VERIFY** your implementation meets the exact requirements
5. Test your changes if testing infrastructure exists

## Phase 2: COMMIT (MANDATORY - DO NOT SKIP)
6. **ADD FILES**: Run `git add .` to stage all changes
7. **COMMIT CHANGES**: Run `git commit -m "implement [feature]: [description]"`  
8. **VERIFY SUCCESS**: Run `git status` - should show "nothing to commit, working tree clean"
9. **GET COMMIT HASH**: Run `git log --oneline -1` to get commit hash

## Phase 3: Report Results
10. Include the required JSON output format with commit hash

# 🚨 ZERO TOLERANCE POLICY 🚨
- If you claim functionality exists, you MUST still implement the EXACT requirements
- If you find similar code, you MUST adapt/extend it to meet the SPECIFIC task
- You MUST create at least one file change for every task
- The reviewer MUST see git diff showing your actual work

Example commit sequence:
```bash
git add .
git commit -m "implement notification service: add NotificationService class and WebSocket integration"  
git status  # Verify success
git log --oneline -1  # Get commit hash
```

# STRICT VALIDATION REQUIREMENTS
Before marking ready_for_review=true, you MUST:
✅ Have modified or created at least one file
✅ Have committed your changes (git status shows clean)
✅ Have tested that your implementation works
✅ Have a commit hash to report

# Required Output Format
After implementing AND committing, you MUST include:

```json:implementation
{
  "rationale": "Brief explanation of what you implemented and why",
  "files_modified": ["list of files you changed - must not be empty"],
  "confidence": 8,
  "testing_notes": "How you verified the solution works exactly as requested",
  "commit_hash": "First 8 characters of git commit hash",
  "committed": true,
  "ready_for_review": true
}
```

# FINAL REMINDER
Your success is measured by:
1. Did you write/modify code files? (files_modified must not be empty)
2. Did you commit changes? (commit_hash must exist)
3. Does your implementation meet the EXACT task requirements?

If any answer is "no", you have failed. The reviewer expects to see actual committed code changes."""
    
    def _load_reviewer_prompt(self) -> str:
        """Load reviewer agent system prompt."""
        return """You are the Reviewer agent in a multi-agent workflow. Your role is to critically review code implementations for quality, correctness, and adherence to best practices.

# Review Criteria
- **Readability**: Is the code easy to understand?
- **Maintainability**: Can this be easily modified later?
- **Consistency**: Does it match existing codebase patterns?
- **Simplicity**: Is this the simplest solution that works?
- **Security**: Are there any security concerns?

# Required Output Format
You MUST provide structured feedback. Start with the JSON immediately after a brief analysis:

```json:review
{
  "approval": false,
  "overall_assessment": "Brief summary of code quality",
  "strengths": ["Top 2-3 positive aspects"],
  "concerns": ["Top 2-3 issues that need addressing"],
  "suggested_fixes": ["Top 2-3 concrete suggestions for improvement"],
  "confidence": 8
}
```

IMPORTANT: 
1. Provide your JSON review block after your analysis
2. Focus on the most critical issues
3. Be thorough but concise in your assessment

# Approval Criteria
Approve (`"approval": true`) only if:
- Code solves the stated problem
- Follows existing codebase patterns  
- Has no significant quality issues
- Handles errors appropriately

Focus on issues that matter - good enough to ship, not perfect."""
    
    def _load_test_planner_prompt(self) -> str:
        """Load test planner agent system prompt."""
        return """You are the Test Planner agent in a multi-agent workflow. Your role is to create comprehensive, structured test plans for successfully implemented features.

# Your Mission
After a feature has been successfully implemented and reviewed, create detailed step-by-step test instructions for manual frontend testing. Focus on real user workflows and edge cases.

# Core Principles
- **User-Centric**: Think like a real user testing the feature
- **Frontend Focus**: All tests must be performed through the UI
- **Comprehensive**: Cover happy paths, edge cases, and error states
- **Clear Instructions**: Write step-by-step instructions anyone can follow
- **Structured Format**: Use consistent formatting for easy readability

# Test Plan Structure
Your test plan MUST follow this exact structure:

## Feature Overview
- Brief summary of what was implemented
- Primary user goals the feature addresses

## Pre-Test Setup
- Any required setup steps before testing
- Data preparation or configuration needed
- User permissions or access requirements

## Test Scenarios

### Scenario 1: [Happy Path Test Name]
**Objective**: [What this test verifies]
**Steps**:
1. [Clear action to take]
2. [Expected result to verify]
3. [Next action]
4. [Continue with specific steps]

**Expected Outcome**: [What should happen if feature works correctly]
**Edge Cases to Check**:
- [Specific edge case 1]
- [Specific edge case 2]

### Scenario 2: [Edge Case Test Name]
[Same structure as Scenario 1]

### Scenario 3: [Error Handling Test Name]
[Same structure as Scenario 1]

## Browser/Device Testing
- List of browsers to test on
- Mobile responsiveness checks if applicable
- Performance considerations

## Acceptance Criteria Verification
- [Checklist of original requirements]
- [Each requirement mapped to test scenario]

# Required Output Format
After analyzing the implementation, provide your test plan in this exact format:

```json:testplan
{
  "feature_name": "Clear, concise feature name",
  "implementation_summary": "Brief description of what was implemented",
  "test_complexity": "simple|moderate|complex",
  "estimated_test_time": "X minutes",
  "requires_data_setup": true/false,
  "confidence": 8
}
```

Then provide the full test plan in markdown format with the structure above.

# Key Guidelines
1. **Be Specific**: "Click the blue Save button" not "save the form"
2. **Verify Results**: Always include what the tester should see/expect
3. **Cover Edge Cases**: Empty inputs, long text, special characters, etc.
4. **Think Mobile**: Consider responsive design and touch interactions
5. **Error Scenarios**: Test validation, network errors, permission issues
6. **Performance**: Loading states, large data sets, slow connections
7. **Accessibility**: Keyboard navigation, screen reader compatibility

# Quality Standards
- Each test scenario should be executable by a non-technical user
- Instructions should be unambiguous and specific
- Cover both positive and negative test cases
- Include visual verification points (colors, text, layouts)
- Test realistic user workflows, not just isolated features

Your test plans enable confident feature releases by ensuring thorough validation."""

    def _create_isolated_workspace(self) -> str:
        """Create isolated git branch for workflow."""
        branch_name = f"wizardry-{self.workflow_id}"
        
        # Ensure we're on the base branch
        self.repo.git.checkout(self.base_branch)
        
        # Create new branch from base
        self.repo.git.checkout('-b', branch_name)
        
        console.print(f"🌟 Created isolated branch: {branch_name}")
        return branch_name
    
    def _register_session(self):
        """Register session for monitoring."""
        registry_file = Path("/tmp/wizardry-sessions/registry.json")
        registry_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(registry_file, 'r') as f:
                registry = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            registry = {}
        
        registry[self.workflow_id] = {
            "session_id": self.workflow_id,
            "repo_path": str(self.original_repo_path),
            "workspace_repo_path": str(self.repo_path),
            "base_branch": self.base_branch,
            "task": self.task,
            "status": "in_progress", 
            "created_at": datetime.now().isoformat(),
            "workspace_path": str(self.session_dir)
        }
        
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
            
        console.print(f"📊 Session registered: {self.workflow_id}")
    
    def _log_conversation(self, agent_name: str, message: str, response: str):
        """Log agent conversations to transcript."""
        transcript_file = self.session_dir / "transcripts" / f"{agent_name}.md"
        
        # Ensure directory exists
        transcript_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(transcript_file, 'a') as f:
            f.write(f"## [{datetime.now().isoformat()}] {agent_name.title()}\n\n")
            f.write(f"**Task**: {message}\n\n")
            f.write(f"**Response**:\n{response}\n\n")
            f.write("---\n\n")
        
        console.print(f"📝 Logged {agent_name} conversation to {transcript_file}")
        console.print(f"📏 Response length: {len(response)} characters")
    
    def _validate_implementation_changes(self, implementation_data: Dict[str, Any]):
        """Validate that implementer actually made and committed changes."""
        current_branch = self.repo.active_branch.name
        
        # Check implementer's claim vs reality
        claimed_committed = implementation_data.get("committed", False)
        claimed_hash = implementation_data.get("commit_hash", "")
        
        # Check if there are any committed changes
        try:
            # Check for commits on current branch vs base branch
            commits_ahead = list(self.repo.iter_commits(f'{self.base_branch}..{current_branch}'))
            
            if commits_ahead:
                console.print(f"✅ Found {len(commits_ahead)} new commit(s) on {current_branch}")
                # Show the most recent commit
                latest_commit = commits_ahead[0]
                actual_hash = latest_commit.hexsha[:8]
                console.print(f"📋 Latest commit: {actual_hash} - {latest_commit.message.strip()}")
                
                # Validate claimed vs actual hash
                if claimed_hash and claimed_hash != actual_hash:
                    console.print(f"⚠️ WARNING: Implementer claimed hash '{claimed_hash}' but actual is '{actual_hash}'")
                
                return
                
        except Exception as e:
            console.print(f"⚠️ Error checking commits: {e}")
        
        # Check for uncommitted changes if no commits found
        is_dirty = self.repo.is_dirty()
        untracked_files = self.repo.untracked_files
        
        if is_dirty or untracked_files:
            console.print("❌ VALIDATION FAILED: Found uncommitted changes!")
            console.print(f"   🎭 Implementer claimed committed={claimed_committed} but this is FALSE")
            if is_dirty:
                console.print("   📝 Modified files found (not committed)")
            if untracked_files:
                console.print(f"   📁 Untracked files: {untracked_files}")
            console.print("   💡 This is exactly why reviewer can't see the changes")
            console.print("   🔧 Implementer needs better commit instruction following")
        else:
            console.print("⚠️ No changes detected - implementer may not have implemented anything")
            console.print("   💡 Consider checking if the task was completed")
    
    async def _run_implementer(self) -> Dict[str, Any]:
        """Run implementer agent session."""
        console.print("🔧 Starting Implementer Agent...")
        
        options = ClaudeCodeOptions(
            system_prompt=self.implementer_prompt,
            max_turns=35,  # Increased to allow more complex implementations
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "LS", "MultiEdit"],
            model="claude-3-5-sonnet-20241022",
            cwd=str(self.repo_path),  # Set working directory to repo
            permission_mode="acceptEdits"  # Critical: Auto-accept file edits
        )
        
        task_prompt = f"""
Task: {self.task}

Please analyze the existing codebase, understand the patterns, and implement the requested functionality. 

Follow the guidelines in your system prompt and make sure to:
1. Study existing code patterns first
2. Implement minimal, clean solution
3. Test your implementation if possible
4. Commit your changes when complete
5. Include the required JSON implementation output
"""
        
        full_response = ""
        async with ClaudeSDKClient(options=options) as client:
            await client.query(task_prompt)
            
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            text = block.text
                            print(text, end='', flush=True)
                            full_response += text
                        elif hasattr(block, 'tool_use'):
                            # Add line breaks before tool usage for better readability
                            tool_break = f"\n\n[Tool: {block.tool_use.name}]\n"
                            print(tool_break, end='', flush=True)
                            full_response += tool_break
                        elif hasattr(block, 'tool_result'):
                            # Add line break after tool results
                            result_break = "\n\n"
                            print(result_break, end='', flush=True) 
                            full_response += result_break
        
        # Log the conversation
        self._log_conversation("implementer", task_prompt, full_response)
        
        # Extract structured output
        try:
            import re
            json_match = re.search(r'```json:implementation\s*\n(.*?)\n```', full_response, re.DOTALL)
            if json_match:
                implementation_data = json.loads(json_match.group(1))
                console.print("✅ Implementer completed with structured output")
                
                # Validate that implementer actually made changes
                self._validate_implementation_changes(implementation_data)
                
                return implementation_data
            else:
                console.print("⚠️ No structured output found, assuming ready for review")
                return {"ready_for_review": True, "rationale": "Implementation completed"}
        except Exception as e:
            console.print(f"⚠️ Error parsing implementer output: {e}")
            return {"ready_for_review": True, "rationale": "Implementation completed"}
    
    async def _run_implementer_with_feedback(self, feedback_prompt: str) -> Dict[str, Any]:
        """Run implementer agent with specific feedback to address."""
        console.print("🔧 Running Implementer with feedback...")
        
        options = ClaudeCodeOptions(
            system_prompt=self.implementer_prompt,
            max_turns=35,  # Increased to allow more complex implementations  
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "LS", "MultiEdit"],
            model="claude-3-5-sonnet-20241022",
            cwd=str(self.repo_path),
            permission_mode="acceptEdits"
        )
        
        full_response = ""
        async with ClaudeSDKClient(options=options) as client:
            await client.query(feedback_prompt)
            
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            text = block.text
                            print(text, end='', flush=True)
                            full_response += text
                        elif hasattr(block, 'tool_use'):
                            # Add line breaks before tool usage for better readability
                            tool_break = f"\n\n[Tool: {block.tool_use.name}]\n"
                            print(tool_break, end='', flush=True)
                            full_response += tool_break
                        elif hasattr(block, 'tool_result'):
                            # Add line break after tool results
                            result_break = "\n\n"
                            print(result_break, end='', flush=True) 
                            full_response += result_break
        
        # Log the conversation
        self._log_conversation("implementer_feedback", feedback_prompt, full_response)
        
        # Extract structured output (same logic as regular implementer)
        try:
            import re
            json_match = re.search(r'```json:implementation\s*\n(.*?)\n```', full_response, re.DOTALL)
            if json_match:
                implementation_data = json.loads(json_match.group(1))
                console.print("✅ Implementer feedback completed with structured output")
                
                # Validate that implementer actually made changes
                self._validate_implementation_changes(implementation_data)
                
                return implementation_data
            else:
                console.print("⚠️ No structured output found in feedback response")
                return {"ready_for_review": False, "rationale": "Failed to address feedback properly"}
        except Exception as e:
            console.print(f"⚠️ Error parsing implementer feedback output: {e}")
            return {"ready_for_review": False, "rationale": "Failed to address feedback properly"}
    
    async def _run_reviewer(self, implementation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run reviewer agent session."""
        console.print("🔍 Starting Reviewer Agent...")
        console.print(f"🔍 Implementation data ready_for_review: {implementation_data.get('ready_for_review', 'Not set')}")
        console.print(f"🔍 Implementation files_modified: {implementation_data.get('files_modified', 'Not specified')}")
        
        # Get git diff for review
        current_branch = self.repo.active_branch.name
        diff_output = ""
        
        try:
            # First try: diff between base branch and current branch
            diff_output = self.repo.git.diff(
                f'{self.base_branch}...{current_branch}',
                '--', '.',
                ':(exclude)wizardry/ui/frontend/.next/**',
                ':(exclude)**/node_modules/**', 
                ':(exclude)**/__pycache__/**',
                ':(exclude)**/*.pyc',
                ':(exclude)**/cache/**'
            )
            console.print(f"📋 Got diff between {self.base_branch}...{current_branch} ({len(diff_output)} chars)")
            
            # If diff is empty, check for uncommitted changes
            if not diff_output.strip():
                console.print("⚠️ No committed changes found, checking for uncommitted changes...")
                # Check for uncommitted changes (staged + unstaged)
                staged_diff = self.repo.git.diff('--cached')
                unstaged_diff = self.repo.git.diff()
                
                console.print(f"📋 Staged diff: {len(staged_diff)} chars, Unstaged diff: {len(unstaged_diff)} chars")
                
                if staged_diff or unstaged_diff:
                    diff_output = f"# Staged changes:\n{staged_diff}\n\n# Unstaged changes:\n{unstaged_diff}"
                    console.print(f"📋 Found uncommitted changes for review ({len(diff_output)} chars total)")
                else:
                    diff_output = "No code changes detected. Please ensure the implementer has committed their work."
            
        except Exception as e:
            console.print(f"⚠️ Error getting git diff: {e}")
            # Enhanced fallback: try simpler three-dot syntax
            try:
                diff_output = self.repo.git.diff(f'{self.base_branch}...HEAD')
                console.print(f"📋 Using simpler three-dot diff as fallback ({len(diff_output)} chars)")
                if not diff_output.strip():
                    diff_output = self.repo.git.diff('--cached')  # staged changes
                    if not diff_output.strip():
                        diff_output = self.repo.git.diff()  # unstaged changes
                        if not diff_output.strip():
                            diff_output = "No code changes detected. Implementation may not have been completed or committed."
            except Exception as fallback_error:
                console.print(f"⚠️ All diff methods failed: {fallback_error}")
                diff_output = f"Error retrieving code changes: {str(e)}\nPlease provide the diff manually for review."
        
        # Handle large diffs by saving to file
        console.print(f"📋 Preparing review with diff length: {len(diff_output)} characters")
        
        diff_file_path = None
        diff_content_for_prompt = diff_output
        
        # If diff is large (>10KB), save to file and tell reviewer to read it
        if len(diff_output) > 10000:
            console.print("📋 Large diff detected - saving to temp file for reviewer")
            try:
                # Save diff to temp file in session directory
                diff_file_path = self.session_dir / "current_diff.txt"
                with open(diff_file_path, 'w') as f:
                    f.write(diff_output)
                console.print(f"📁 Saved diff to: {diff_file_path}")
                
                # Replace diff content in prompt with file reference
                diff_content_for_prompt = f"[DIFF TOO LARGE - {len(diff_output)} chars]\nPlease use the Read tool to view: {diff_file_path}"
            except Exception as e:
                console.print(f"⚠️ Failed to save diff to file: {e}")
                # Fall back to including truncated diff
                diff_content_for_prompt = diff_output[:5000] + f"\n\n... [TRUNCATED - showing first 5KB of {len(diff_output)} total chars] ...\n\nPlease use git diff command for full changes."

        options = ClaudeCodeOptions(
            system_prompt=self.reviewer_prompt,
            max_turns=8,  # Allow enough turns for thorough review and tool usage
            allowed_tools=["Read", "Grep", "Bash", "LS"],
            model="claude-3-5-sonnet-20241022",
            cwd=str(self.repo_path),  # Set working directory to repo
            permission_mode="acceptEdits"  # Allow reviewing files
        )
        
        review_prompt = f"""
Please review this implementation:

**Original Task**: {self.task}

**Implementation Details**: {json.dumps(implementation_data, indent=2)}

**Git Diff**:
```diff
{diff_content_for_prompt}
```

**Instructions**: 
Review the code changes efficiently:

1. **If git diff is available**: Focus on the key changes and their impact
2. **If no changes detected**: Use tools to investigate (git status, git log, Read files)
3. **Keep review concise**: Focus on the most critical issues only
4. **Prioritize**: Security > Correctness > Code Quality > Style

Analyze for:
- Does it solve the stated problem?
- Are there security/correctness issues?
- Does it follow existing patterns?
- Any critical improvements needed?

Provide your structured JSON review - be concise and actionable.
"""
        
        if diff_output and len(diff_output.strip()) > 0:
            console.print("✅ Diff contains actual code changes")
        else:
            console.print("⚠️ Diff is empty or contains no changes")
        
        full_response = ""
        async with ClaudeSDKClient(options=options) as client:
            await client.query(review_prompt)
            
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            text = block.text
                            print(text, end='', flush=True)
                            full_response += text
                        elif hasattr(block, 'tool_use'):
                            # Add line breaks before tool usage for better readability
                            tool_break = f"\n\n[Tool: {block.tool_use.name}]\n"
                            print(tool_break, end='', flush=True)
                            full_response += tool_break
                        elif hasattr(block, 'tool_result'):
                            # Add line break after tool results
                            result_break = "\n\n"
                            print(result_break, end='', flush=True) 
                            full_response += result_break
        
        # Log the conversation
        self._log_conversation("reviewer", review_prompt, full_response)
        
        # Extract structured output
        try:
            import re
            json_match = re.search(r'```json:review\s*\n(.*?)\n```', full_response, re.DOTALL)
            if json_match:
                review_data = json.loads(json_match.group(1))
                console.print(f"✅ Reviewer completed with approval: {review_data.get('approval', False)}")
                return review_data
            else:
                console.print("⚠️ No structured review found - response may be incomplete!")
                console.print(f"📋 Response length: {len(full_response)} characters")
                console.print("📋 Response preview:", full_response[-200:] if len(full_response) > 200 else full_response)
                
                # If response looks truncated (ends without proper JSON), indicate incomplete review
                if len(full_response) > 1000 and not full_response.endswith('```'):
                    return {"approval": False, "overall_assessment": "Review incomplete - response was truncated", "concerns": ["Reviewer response was cut off mid-analysis"]}
                else:
                    return {"approval": False, "overall_assessment": "Review failed - no structured output", "concerns": ["No structured review output provided"]}
        except Exception as e:
            console.print(f"⚠️ Error parsing review output: {e}")
            console.print(f"📋 Response length: {len(full_response)} characters")
            console.print("📋 Response preview:", full_response[-200:] if len(full_response) > 200 else full_response)
            return {"approval": False, "overall_assessment": f"Review failed - parsing error: {e}", "concerns": [f"Failed to parse review output: {e}"]}
    
    async def _run_test_planner(self, implementation_data: Dict[str, Any], review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run test planner agent session."""
        console.print("📋 Starting Test Planner Agent...")
        
        # Get git diff for test planning context
        current_branch = self.repo.active_branch.name
        diff_output = ""
        
        try:
            # Get diff for understanding what was implemented
            diff_output = self.repo.git.diff(
                f'{self.base_branch}...{current_branch}',
                '--', '.',
                ':(exclude)wizardry/ui/frontend/.next/**',
                ':(exclude)**/node_modules/**', 
                ':(exclude)**/__pycache__/**',
                ':(exclude)**/*.pyc',
                ':(exclude)**/cache/**'
            )
            console.print(f"📋 Got diff for test planning ({len(diff_output)} chars)")
            
            if not diff_output.strip():
                # Check for uncommitted changes as fallback
                staged_diff = self.repo.git.diff('--cached')
                unstaged_diff = self.repo.git.diff()
                if staged_diff or unstaged_diff:
                    diff_output = f"# Staged changes:\n{staged_diff}\n\n# Unstaged changes:\n{unstaged_diff}"
                else:
                    diff_output = "No code changes detected for test planning."
            
        except Exception as e:
            console.print(f"⚠️ Error getting git diff for test planner: {e}")
            diff_output = f"Error retrieving code changes: {str(e)}"

        # Handle large diffs by saving to file
        diff_file_path = None
        diff_content_for_prompt = diff_output
        
        if len(diff_output) > 8000:
            console.print("📋 Large diff detected - saving to temp file for test planner")
            try:
                diff_file_path = self.session_dir / "test_planning_diff.txt"
                with open(diff_file_path, 'w') as f:
                    f.write(diff_output)
                console.print(f"📁 Saved diff to: {diff_file_path}")
                
                diff_content_for_prompt = f"[DIFF TOO LARGE - {len(diff_output)} chars]\nPlease use the Read tool to view: {diff_file_path}"
            except Exception as e:
                console.print(f"⚠️ Failed to save diff to file: {e}")
                diff_content_for_prompt = diff_output[:4000] + f"\n\n... [TRUNCATED - showing first 4KB of {len(diff_output)} total chars] ..."

        options = ClaudeCodeOptions(
            system_prompt=self.test_planner_prompt,
            max_turns=12,
            allowed_tools=["Read", "Grep", "Bash", "LS"],
            model="claude-3-5-sonnet-20241022",
            cwd=str(self.repo_path),
            permission_mode="acceptEdits"
        )
        
        test_plan_prompt = f"""
Please create a comprehensive test plan for this implemented feature:

**Original Task**: {self.task}

**Implementation Summary**: {json.dumps(implementation_data, indent=2)}

**Review Results**: {json.dumps(review_data, indent=2)}

**Code Changes**:
```diff
{diff_content_for_prompt}
```

**Instructions**: 
Analyze the implementation and create a detailed test plan focusing on:

1. **Understanding the Feature**: Study the code changes and original task to understand what was built
2. **User Workflows**: Identify the primary user journeys this feature enables
3. **Test Scenarios**: Create specific, actionable test cases for frontend validation
4. **Edge Cases**: Consider error states, boundary conditions, and unusual inputs
5. **Integration Points**: Test how this feature works with existing functionality

Focus on creating tests that can be executed by non-technical users through the frontend interface. Include specific UI elements to interact with, expected visual feedback, and clear success criteria.

Provide your structured JSON test plan data followed by the detailed markdown test plan.
"""
        
        full_response = ""
        async with ClaudeSDKClient(options=options) as client:
            await client.query(test_plan_prompt)
            
            async for message in client.receive_response():
                if hasattr(message, 'content'):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            text = block.text
                            print(text, end='', flush=True)
                            full_response += text
                        elif hasattr(block, 'tool_use'):
                            tool_break = f"\n\n[Tool: {block.tool_use.name}]\n"
                            print(tool_break, end='', flush=True)
                            full_response += tool_break
                        elif hasattr(block, 'tool_result'):
                            result_break = "\n\n"
                            print(result_break, end='', flush=True) 
                            full_response += result_break
        
        # Log the conversation
        self._log_conversation("test_planner", test_plan_prompt, full_response)
        
        # Save the full test plan to a file for easy access
        try:
            test_plan_file = self.session_dir / "test_plan.md"
            with open(test_plan_file, 'w') as f:
                f.write(f"# Test Plan for: {self.task}\n\n")
                f.write(f"**Generated**: {datetime.now().isoformat()}\n")
                f.write(f"**Session ID**: {self.workflow_id}\n\n")
                f.write("---\n\n")
                f.write(full_response)
            console.print(f"📋 Test plan saved to: {test_plan_file}")
        except Exception as e:
            console.print(f"⚠️ Failed to save test plan to file: {e}")
        
        # Extract structured output
        try:
            import re
            json_match = re.search(r'```json:testplan\s*\n(.*?)\n```', full_response, re.DOTALL)
            if json_match:
                test_plan_data = json.loads(json_match.group(1))
                console.print(f"✅ Test Planner completed - Feature: {test_plan_data.get('feature_name', 'Unknown')}")
                console.print(f"📋 Complexity: {test_plan_data.get('test_complexity', 'Unknown')}, Est. Time: {test_plan_data.get('estimated_test_time', 'Unknown')}")
                
                # Add the full response as test plan content
                test_plan_data["test_plan_content"] = full_response
                test_plan_data["test_plan_generated"] = True
                
                return test_plan_data
            else:
                console.print("⚠️ No structured test plan output found")
                return {
                    "test_plan_generated": False, 
                    "error": "No structured output found",
                    "test_plan_content": full_response
                }
        except Exception as e:
            console.print(f"⚠️ Error parsing test plan output: {e}")
            return {
                "test_plan_generated": False, 
                "error": f"Parsing error: {e}",
                "test_plan_content": full_response
            }
    
    def _create_pr(self):
        """Create GitHub PR for the implementation."""
        current_branch = self.repo.active_branch.name
        
        pr_title = f"🤖 {self.task[:60]}{'...' if len(self.task) > 60 else ''}"
        pr_body = f"""## Automated Workflow Implementation

**Task**: {self.task}
**Workflow ID**: {self.workflow_id}
**Base Branch**: {self.base_branch}  
**Implementation Branch**: {current_branch}

## Agent Workflow
This PR was created by the Wizardry multi-agent workflow system:
- **Implementer**: Analyzed codebase and implemented solution
- **Reviewer**: Reviewed code quality and approved changes

## Transcripts
Full agent conversations available at: `/tmp/wizardry-sessions/{self.workflow_id}/transcripts/`

---
🤖 Generated by Wizardry Agent Orchestrator"""
        
        try:
            # Use gh CLI to create PR
            import subprocess
            result = subprocess.run([
                "gh", "pr", "create", 
                "--base", self.base_branch,
                "--head", current_branch,
                "--title", pr_title,
                "--body", pr_body
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print("✅ Pull request created successfully!")
                console.print(f"PR URL: {result.stdout.strip()}")
                return result.stdout.strip()
            else:
                console.print(f"❌ Failed to create PR: {result.stderr}")
                return None
        except Exception as e:
            console.print(f"❌ Error creating PR: {e}")
            return None
    
    async def _sync_to_original_repo(self):
        """Sync changes from workspace repo back to original repo if needed."""
        if self.repo_path == self.original_repo_path:
            # No workspace copy - nothing to sync
            return
            
        try:
            import subprocess
            import shutil
            current_branch = self.repo.active_branch.name
            
            console.print(f"🔄 Syncing changes from workspace to original repo...")
            
            # Switch to original repo and create/update the branch
            original_repo = Repo(self.original_repo_path)
            
            # Fetch the workspace repo as a remote and merge the branch
            workspace_remote_name = f"workspace_{self.workflow_id[:8]}"
            
            # Add workspace as temporary remote
            result = subprocess.run([
                "git", "-C", str(self.original_repo_path), "remote", "add", 
                workspace_remote_name, str(self.repo_path)
            ], capture_output=True, text=True)
            
            # Fetch the branch from workspace
            result = subprocess.run([
                "git", "-C", str(self.original_repo_path), "fetch", 
                workspace_remote_name, current_branch
            ], check=True, capture_output=True, text=True)
            
            # Create/update the branch in original repo
            result = subprocess.run([
                "git", "-C", str(self.original_repo_path), "branch", "-f",
                current_branch, f"{workspace_remote_name}/{current_branch}"
            ], check=True, capture_output=True, text=True)
            
            # Clean up the temporary remote
            subprocess.run([
                "git", "-C", str(self.original_repo_path), "remote", "remove", 
                workspace_remote_name
            ], capture_output=True, text=True)
            
            console.print(f"✅ Successfully synced branch '{current_branch}' to original repo")
            
        except subprocess.CalledProcessError as e:
            console.print(f"⚠️ Failed to sync to original repo: {e.stderr}")
            console.print(f"📋 Manual sync required - check workspace at: {self.repo_path}")
        except Exception as e:
            console.print(f"⚠️ Error during repo sync: {e}")
    
    def _cleanup_worktree(self):
        """Clean up the git worktree after workflow completion."""
        if self.repo_path == self.original_repo_path:
            return  # No worktree to clean up
            
        try:
            import subprocess
            worktree_branch = f"wizardry-{self.workflow_id}"
            
            # Remove worktree
            result = subprocess.run([
                "git", "-C", str(self.original_repo_path),
                "worktree", "remove", str(self.repo_path)
            ], check=True, capture_output=True, text=True)
            
            console.print(f"🧹 Cleaned up worktree: {self.repo_path}")
            
            # Optionally remove the branch (but keep it for reference)
            # subprocess.run(["git", "-C", str(self.original_repo_path), "branch", "-D", worktree_branch])
            
        except subprocess.CalledProcessError as e:
            console.print(f"⚠️ Failed to clean up worktree: {e.stderr}")
        except Exception as e:
            console.print(f"⚠️ Error during worktree cleanup: {e}")
    
    @staticmethod
    def archive_session(session_id: str, cleanup_branch: bool = True) -> bool:
        """Archive a session and clean up all associated resources."""
        registry_file = Path("/tmp/wizardry-sessions/registry.json")
        archived_dir = Path("/tmp/wizardry-sessions/archived")
        
        try:
            # Load session registry
            if not registry_file.exists():
                console.print(f"❌ Registry file not found")
                return False
                
            with open(registry_file, 'r') as f:
                registry = json.load(f)
                
            if session_id not in registry:
                console.print(f"❌ Session {session_id} not found in registry")
                return False
                
            session = registry[session_id]
            session_dir = Path(session["workspace_path"])
            original_repo_path = session.get("repo_path", "")
            workspace_repo_path = session.get("workspace_repo_path", "")
            
            console.print(f"🗂️ Archiving session {session_id}...")
            
            # 1. Move session to archived directory
            archived_dir.mkdir(exist_ok=True, parents=True)
            archived_session_dir = archived_dir / session_id
            
            if session_dir.exists():
                import shutil
                if archived_session_dir.exists():
                    shutil.rmtree(archived_session_dir)
                shutil.move(str(session_dir), str(archived_session_dir))
                console.print(f"📦 Moved session files to: {archived_session_dir}")
            
            # 2. Clean up branch if requested and if we have repo info
            if cleanup_branch and original_repo_path and session.get("status") in ["completed", "failed", "terminated"]:
                try:
                    # Find the branch name from session logs or use pattern
                    branch_pattern = f"wizardry-*{session_id[-6:]}"  # Use last 6 chars of session ID
                    
                    import subprocess
                    # List branches matching the pattern
                    result = subprocess.run([
                        "git", "-C", original_repo_path, "branch", "--list", branch_pattern
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        branches = [b.strip().lstrip('* ') for b in result.stdout.strip().split('\n')]
                        for branch in branches:
                            if branch and branch != session.get("base_branch"):
                                # Delete the branch
                                result = subprocess.run([
                                    "git", "-C", original_repo_path, "branch", "-D", branch
                                ], capture_output=True, text=True)
                                
                                if result.returncode == 0:
                                    console.print(f"🗑️ Deleted branch: {branch}")
                                else:
                                    console.print(f"⚠️ Failed to delete branch {branch}: {result.stderr}")
                                    
                except Exception as e:
                    console.print(f"⚠️ Error cleaning up branch: {e}")
            
            # 3. Clean up git worktree if it exists and is different from original
            if workspace_repo_path and workspace_repo_path != original_repo_path:
                workspace_path = Path(workspace_repo_path)
                if workspace_path.exists() and workspace_path != Path(original_repo_path):
                    try:
                        import subprocess
                        # First try to remove the worktree using git worktree remove
                        result = subprocess.run([
                            "git", "-C", original_repo_path, "worktree", "remove", str(workspace_path)
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            console.print(f"🗑️ Removed git worktree: {workspace_path}")
                        else:
                            # If git worktree remove fails, try force removal and then manual cleanup
                            console.print(f"⚠️ Git worktree remove failed: {result.stderr}")
                            
                            # Force remove from git's worktree list
                            subprocess.run([
                                "git", "-C", original_repo_path, "worktree", "remove", "--force", str(workspace_path)
                            ], capture_output=True, text=True)
                            
                            # Manually clean up directory if it still exists
                            if workspace_path.exists():
                                import shutil
                                shutil.rmtree(workspace_path)
                                console.print(f"🗑️ Manually cleaned up workspace directory: {workspace_path}")
                    except Exception as e:
                        console.print(f"⚠️ Failed to clean up git worktree: {e}")
                        # Fallback to manual directory cleanup
                        try:
                            if workspace_path.exists():
                                import shutil
                                shutil.rmtree(workspace_path)
                                console.print(f"🗑️ Fallback cleanup of workspace directory: {workspace_path}")
                        except Exception as fallback_e:
                            console.print(f"⚠️ Fallback cleanup also failed: {fallback_e}")
            
            # 4. Remove from active registry
            del registry[session_id]
            with open(registry_file, 'w') as f:
                json.dump(registry, f, indent=2)
            
            console.print(f"✅ Session {session_id} archived successfully")
            return True
            
        except Exception as e:
            console.print(f"❌ Error archiving session {session_id}: {e}")
            return False
    
    async def run_workflow(self) -> bool:
        """Run the complete workflow."""
        console.print(f"🚀 Starting Wizardry workflow: {self.workflow_id}")
        console.print(f"📋 Task: {self.task}")
        console.print(f"🌿 Base branch: {self.base_branch}")
        
        try:
            # Workspace already set up by _setup_workspace_repo() in constructor
            self._register_session()
            
            # Run implementer
            with console.status("🔧 Implementer working..."):
                implementation_data = await self._run_implementer()
            
            if not implementation_data.get("ready_for_review", False):
                console.print("❌ Implementer did not complete successfully")
                return False
            
            # Run reviewer  
            with console.status("🔍 Reviewer analyzing..."):
                review_data = await self._run_reviewer(implementation_data)
            
            # Check approval
            max_iterations = 2
            iteration = 1
            
            while not review_data.get("approval", False) and iteration <= max_iterations:
                console.print(f"❌ Review rejected (iteration {iteration}/{max_iterations})")
                console.print("Feedback:", review_data.get("suggested_fixes", []))
                
                # Re-run implementer with feedback
                console.print(f"🔄 Re-running implementer with feedback (iteration {iteration + 1})")
                
                # Create feedback prompt for implementer
                feedback_prompt = f"""
The reviewer has provided feedback on your implementation. Please address these issues:

**Original Task**: {self.task}

**Previous Implementation**: {json.dumps(implementation_data, indent=2)}

**Reviewer Feedback**:
- Overall Assessment: {review_data.get("overall_assessment", "Not provided")}
- Concerns: {review_data.get("concerns", [])}
- Suggested Fixes: {review_data.get("suggested_fixes", [])}

Please fix these issues and commit your changes. Make sure to:
1. Address all the concerns mentioned
2. Follow the suggested fixes
3. Test your changes
4. Commit with git add && git commit
5. Provide the required JSON implementation output
"""
                
                with console.status(f"🔧 Implementer fixing issues (iteration {iteration + 1})..."):
                    implementation_data = await self._run_implementer_with_feedback(feedback_prompt)
                
                if not implementation_data.get("ready_for_review", False):
                    console.print(f"❌ Implementer failed to address feedback (iteration {iteration + 1})")
                    break
                
                # Re-review the updated implementation
                with console.status(f"🔍 Reviewer re-analyzing (iteration {iteration + 1})..."):
                    review_data = await self._run_reviewer(implementation_data)
                
                iteration += 1
            
            if review_data.get("approval", False):
                console.print("✅ Review approved!")

                # Run test planner after successful review
                console.print("📋 Starting test planning phase...")
                test_plan_data = {}
                try:
                    with console.status("📋 Test Planner analyzing implementation..."):
                        test_plan_data = await self._run_test_planner(implementation_data, review_data)
                    
                    if test_plan_data.get("test_plan_generated", False):
                        console.print("✅ Test plan generated successfully!")
                        console.print(f"📋 Feature: {test_plan_data.get('feature_name', 'Unknown')}")
                        console.print(f"📋 Test complexity: {test_plan_data.get('test_complexity', 'Unknown')}")
                        console.print(f"📋 Estimated test time: {test_plan_data.get('estimated_test_time', 'Unknown')}")
                    else:
                        console.print("⚠️ Test plan generation had issues, but workflow continues")
                except Exception as e:
                    console.print(f"⚠️ Test planning failed: {e}")                
                # Sync changes back to original repo if we're using a workspace copy
                await self._sync_to_original_repo()
                
                # Create PR
                pr_url = self._create_pr()
                
                # Keep worktree for diff viewing - cleanup happens during session archive
                
                console.print("🎉 Workflow completed successfully!")
                if test_plan_data.get("test_plan_generated", False):
                    console.print("📋 Test plan is ready! Check the UI for detailed testing instructions.")
                success = True
            else:
                console.print("❌ Workflow failed after max iterations")
                success = False
                
        except Exception as e:
            console.print(f"❌ Workflow error: {e}")
            success = False
        finally:
            # Worktree cleanup handled during session archive, not here
                
            # Update session status based on actual result
            if success:
                status = "ready_to_test" if ('test_plan_data' in locals() and test_plan_data.get("test_plan_generated", False)) else "completed"
            else:
                status = "failed"
            self._update_session_status(status)
            console.print(f"📊 Session status updated: {status}")
        
        return success
    
    def _update_session_status(self, status: str):
        """Update session status in registry."""
        registry_file = Path("/tmp/wizardry-sessions/registry.json")
        try:
            with open(registry_file, 'r') as f:
                registry = json.load(f)
            
            if self.workflow_id in registry:
                registry[self.workflow_id]["status"] = status
                
                with open(registry_file, 'w') as f:
                    json.dump(registry, f, indent=2)
        except Exception:
            pass  # Session tracking is not critical


async def run_orchestrator(repo_path: str, branch: str, task: str) -> bool:
    """Entry point for running orchestrated workflow."""
    orchestrator = WorkflowOrchestrator(repo_path, branch, task)
    return await orchestrator.run_workflow()
