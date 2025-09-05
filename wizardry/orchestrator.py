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
        self.repo_path = Path(repo_path).resolve()
        self.base_branch = base_branch
        self.task = task
        self.workflow_id = self._generate_workflow_id()
        self.repo = Repo(self.repo_path)
        
        # Session tracking
        self.session_dir = Path(f"/tmp/wizardry-sessions/{self.workflow_id}")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        (self.session_dir / "transcripts").mkdir(exist_ok=True)
        
        # Agent configurations
        self.implementer_prompt = self._load_implementer_prompt()
        self.reviewer_prompt = self._load_reviewer_prompt()
        
    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = str(int(time.time()))
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
        return f"workflow-{timestamp}-{random_suffix}"
    
    def _load_implementer_prompt(self) -> str:
        """Load implementer agent system prompt."""
        return """You are the Implementer agent in a multi-agent workflow. Your role is to analyze tasks and implement clean, minimal solutions.

# CRITICAL: You MUST actually write code and commit it!

# Core Principles
- **Minimal Invasiveness**: Make the smallest, cleanest change necessary to solve the problem
- **PMF Mentality**: Prioritize making something that works over perfect architecture
- **Clean Code**: Write readable, maintainable code that follows existing patterns
- **No Assumptions**: Only use libraries/frameworks that already exist in the codebase
- **Follow Conventions**: Match existing code style, naming, and patterns exactly

# Your Process (MUST DO ALL STEPS)
1. Analyze the task and understand the existing codebase
2. Identify the minimal change needed
3. **ACTUALLY IMPLEMENT** - use Write/Edit tools to create/modify files
4. Test your changes if testing infrastructure exists  
5. **COMMIT YOUR WORK** - MANDATORY: git add . && git commit -m "descriptive message"
6. **VERIFY COMMIT** - run git status to confirm commit succeeded
7. Include the required JSON output format

# COMMIT IS ABSOLUTELY REQUIRED
If you do not commit your changes, the reviewer will NOT be able to see them and the workflow will FAIL.
ALWAYS run: git add . && git commit -m "implement [feature]: [brief description]"
Then verify with: git status

# CRITICAL REQUIREMENTS
- You MUST use Write/Edit tools to create actual code files
- You MUST commit your changes with git add && git commit
- Do NOT just plan or discuss - ACTUALLY IMPLEMENT AND COMMIT
- The reviewer expects to see a git diff with actual changes

# Required Output Format
After implementing AND committing, you MUST include:

```json:implementation
{
  "rationale": "Brief explanation of your approach and why",
  "files_modified": ["list of files you changed"],
  "confidence": 8,
  "testing_notes": "How you verified the solution works",
  "commit_hash": "First 8 characters of git commit hash",
  "committed": true,
  "ready_for_review": true
}
```

CRITICAL: Do not mark ready_for_review as true unless you have successfully committed your changes!

Remember: Your job is to SHIP CODE, not just talk about it. Write files, commit changes, then provide the JSON output."""
    
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
            "repo_path": str(self.repo_path),
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
        
        # Check if there are any committed changes
        try:
            # Check for commits on current branch vs base branch
            commits_ahead = list(self.repo.iter_commits(f'{self.base_branch}..{current_branch}'))
            
            if commits_ahead:
                console.print(f"✅ Found {len(commits_ahead)} new commit(s) on {current_branch}")
                # Show the most recent commit
                latest_commit = commits_ahead[0]
                console.print(f"📋 Latest commit: {latest_commit.hexsha[:8]} - {latest_commit.message.strip()}")
                return
                
        except Exception as e:
            console.print(f"⚠️ Error checking commits: {e}")
        
        # Check for uncommitted changes if no commits found
        is_dirty = self.repo.is_dirty()
        untracked_files = self.repo.untracked_files
        
        if is_dirty or untracked_files:
            console.print("⚠️ Found uncommitted changes - implementer may have forgotten to commit!")
            if is_dirty:
                console.print("   📝 Modified files found")
            if untracked_files:
                console.print(f"   📁 Untracked files: {untracked_files}")
            console.print("   💡 This might be why reviewer can't see the changes")
        else:
            console.print("⚠️ No changes detected - implementer may not have implemented anything")
            console.print("   💡 Consider checking if the task was completed")
    
    async def _run_implementer(self) -> Dict[str, Any]:
        """Run implementer agent session."""
        console.print("🔧 Starting Implementer Agent...")
        
        options = ClaudeCodeOptions(
            system_prompt=self.implementer_prompt,
            max_turns=10,
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
            max_turns=10,
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
            diff_output = self.repo.git.diff(self.base_branch, current_branch)
            console.print(f"📋 Got diff between {self.base_branch} and {current_branch} ({len(diff_output)} chars)")
            
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
                    # Last resort: try HEAD~1 to HEAD if there are recent commits
                    try:
                        diff_output = self.repo.git.diff('HEAD~1', 'HEAD')
                        console.print(f"📋 Using last commit diff as fallback ({len(diff_output)} chars)")
                    except Exception as e:
                        console.print(f"⚠️ No changes found for review: {e}")
                        diff_output = "No code changes detected. Please ensure the implementer has committed their work."
            
        except Exception as e:
            console.print(f"⚠️ Error getting git diff: {e}")
            # Enhanced fallback: try multiple approaches
            try:
                # Try to get any changes at all
                diff_output = self.repo.git.diff('HEAD~1', 'HEAD')
                if not diff_output.strip():
                    diff_output = self.repo.git.diff('--cached')  # staged changes
                    if not diff_output.strip():
                        diff_output = self.repo.git.diff()  # unstaged changes
                        if not diff_output.strip():
                            diff_output = "No code changes detected. Implementation may not have been completed or committed."
            except Exception as fallback_error:
                console.print(f"⚠️ All diff methods failed: {fallback_error}")
                diff_output = f"Error retrieving code changes: {str(e)}\nPlease provide the diff manually for review."
        
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
{diff_output}
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
        
        # Log diff size but don't truncate - let reviewer handle the full context
        console.print(f"📋 Sending review prompt with diff length: {len(diff_output)} characters")
        if len(diff_output) > 10000:
            console.print("📋 Large diff - reviewer will focus on key changes")
        
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
    
    async def run_workflow(self) -> bool:
        """Run the complete workflow."""
        console.print(f"🚀 Starting Wizardry workflow: {self.workflow_id}")
        console.print(f"📋 Task: {self.task}")
        console.print(f"🌿 Base branch: {self.base_branch}")
        
        try:
            # Setup isolated workspace
            isolated_branch = self._create_isolated_workspace()
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
                
                # Create PR
                pr_url = self._create_pr()
                
                console.print("🎉 Workflow completed successfully!")
                success = True
            else:
                console.print("❌ Workflow failed after max iterations")
                success = False
                
        except Exception as e:
            console.print(f"❌ Workflow error: {e}")
            success = False
        finally:
            # Update session status based on actual result
            status = "completed" if success else "failed"
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