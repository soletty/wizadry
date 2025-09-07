"""FastAPI backend for Wizardry UI."""

import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import existing Wizardry functionality
import sys
current_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(current_dir))

from wizardry.orchestrator import run_orchestrator, WorkflowOrchestrator
from git import Repo, InvalidGitRepositoryError


app = FastAPI(title="Wizardry API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3005"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()


# Pydantic models
class CreateSessionRequest(BaseModel):
    repo_path: str
    base_branch: str
    task: str
    no_cleanup: bool = False
    max_iterations: int = 2


class RepoInfo(BaseModel):
    path: str
    name: str
    branches: List[str]
    current_branch: str
    is_clean: bool
    remote_url: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    repo_path: str
    base_branch: str
    task: str
    status: str
    created_at: str
    workspace_path: str
    terminated_at: Optional[str] = None


class TranscriptResponse(BaseModel):
    implementer: str
    reviewer: str


class ConversationEntry(BaseModel):
    timestamp: str
    agent: str  # "implementer" or "reviewer"
    task: str
    response: str


class ConversationResponse(BaseModel):
    conversation: List[ConversationEntry]


class TestPlanResponse(BaseModel):
    feature_name: str
    implementation_summary: str
    test_complexity: str
    estimated_test_time: str
    requires_data_setup: bool
    confidence: int
    test_plan_content: str
    test_plan_generated: bool = True


# Utility functions
def get_session_registry_path() -> Path:
    """Get the session registry path."""
    return Path("/tmp/wizardry-sessions/registry.json")


def load_sessions() -> Dict[str, Any]:
    """Load active sessions from registry."""
    registry_file = get_session_registry_path()
    if not registry_file.exists():
        return {}
    
    try:
        with open(registry_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_sessions(sessions: Dict[str, Any]):
    """Save sessions to registry."""
    registry_file = get_session_registry_path()
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(registry_file, 'w') as f:
        json.dump(sessions, f, indent=2)


def get_repo_info(repo_path: str) -> Optional[RepoInfo]:
    """Get repository information including branches."""
    try:
        repo = Repo(repo_path)
        
        # Get all branches
        branches = []
        try:
            for branch in repo.branches:
                branches.append(branch.name)
        except Exception:
            branches = ["main", "master"]  # fallback
        
        # Get current branch
        current_branch = None
        try:
            current_branch = repo.active_branch.name
        except Exception:
            current_branch = "main"
        
        # Get remote URL
        remote_url = None
        try:
            if repo.remotes:
                remote_url = repo.remotes.origin.url
        except Exception:
            pass
        
        return RepoInfo(
            path=repo_path,
            name=Path(repo_path).name,
            branches=branches,
            current_branch=current_branch,
            is_clean=not repo.is_dirty(),
            remote_url=remote_url
        )
    except InvalidGitRepositoryError:
        return None


def parse_transcript_entries(transcript_content: str, agent_name: str) -> List[ConversationEntry]:
    """Parse transcript markdown content into conversation entries."""
    entries = []
    
    if not transcript_content.strip():
        return entries
    
    # Split by the actual separator "---\n\n" (not just "---" which appears in git diffs)
    sections = transcript_content.split('---\n\n')
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Extract timestamp from header like "## [2024-01-01T12:00:00] Implementer"
        lines = section.split('\n')
        timestamp = ""
        task = ""
        response = ""
        
        # Find timestamp in first line
        if lines and lines[0].startswith('## ['):
            timestamp_match = lines[0]
            start = timestamp_match.find('[') + 1
            end = timestamp_match.find(']')
            if start > 0 and end > start:
                timestamp = timestamp_match[start:end]
        
        # Find task and response
        task_start = -1
        response_start = -1
        
        for i, line in enumerate(lines):
            if line.startswith('**Task**:'):
                task_start = i
            elif line.startswith('**Response**:'):
                response_start = i
                break
        
        if task_start >= 0:
            # Extract task (everything after **Task**: until **Response**: or end)
            if response_start > task_start:
                task = '\n'.join(lines[task_start+1:response_start]).strip()
                response = '\n'.join(lines[response_start+1:]).strip()
            else:
                task = '\n'.join(lines[task_start+1:]).strip()
        
        if timestamp and (task or response):
            entries.append(ConversationEntry(
                timestamp=timestamp,
                agent=agent_name,
                task=task,
                response=response
            ))
    
    return entries


def find_git_repos(search_path: str = ".", max_depth: int = 3) -> List[RepoInfo]:
    """Find git repositories in the given path."""
    repos = []
    search_path = Path(search_path).expanduser().resolve()
    
    def scan_directory(path: Path, depth: int):
        if depth > max_depth:
            return
        
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if this directory is a git repo
                    if (item / '.git').exists():
                        repo_info = get_repo_info(str(item))
                        if repo_info:
                            repos.append(repo_info)
                    else:
                        # Recurse into subdirectories
                        scan_directory(item, depth + 1)
        except (PermissionError, FileNotFoundError):
            pass
    
    # Always add current directory if it's a git repo
    current_repo = get_repo_info(str(search_path))
    if current_repo:
        repos.append(current_repo)
    
    # Scan for other repos
    scan_directory(search_path, 0)
    
    # Remove duplicates based on path
    seen_paths = set()
    unique_repos = []
    for repo in repos:
        if repo.path not in seen_paths:
            seen_paths.add(repo.path)
            unique_repos.append(repo)
    
    return unique_repos


async def run_workflow_background(request: CreateSessionRequest):
    """Run workflow in the background and update WebSocket clients."""
    try:
        success = await run_orchestrator(
            request.repo_path, 
            request.base_branch, 
            request.task
        )
        
        # Broadcast completion to all connected clients
        message = json.dumps({
            "type": "workflow_completed",
            "success": success,
            "repo_path": request.repo_path,
            "task": request.task
        })
        await manager.broadcast(message)
        
    except Exception as e:
        # Broadcast error to all connected clients
        message = json.dumps({
            "type": "workflow_error",
            "error": str(e),
            "repo_path": request.repo_path,
            "task": request.task
        })
        await manager.broadcast(message)


# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "wizardry-api"}


@app.get("/api/sessions", response_model=List[SessionInfo])
async def get_sessions():
    """Get all sessions."""
    sessions_data = load_sessions()
    sessions = []
    
    for session_id, session_data in sessions_data.items():
        sessions.append(SessionInfo(
            session_id=session_id,
            repo_path=session_data.get("repo_path", ""),
            base_branch=session_data.get("base_branch", ""),
            task=session_data.get("task", ""),
            status=session_data.get("status", "unknown"),
            created_at=session_data.get("created_at", ""),
            workspace_path=session_data.get("workspace_path", ""),
            terminated_at=session_data.get("terminated_at")
        ))
    
    # Sort by creation time, newest first
    sessions.sort(key=lambda x: x.created_at, reverse=True)
    return sessions


@app.get("/api/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get specific session details."""
    sessions = load_sessions()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        repo_path=session_data.get("repo_path", ""),
        base_branch=session_data.get("base_branch", ""),
        task=session_data.get("task", ""),
        status=session_data.get("status", "unknown"),
        created_at=session_data.get("created_at", ""),
        workspace_path=session_data.get("workspace_path", ""),
        terminated_at=session_data.get("terminated_at")
    )


@app.post("/api/sessions")
async def create_session(request: CreateSessionRequest, background_tasks: BackgroundTasks):
    """Create a new workflow session."""
    # Validate repository
    repo_info = get_repo_info(request.repo_path)
    if not repo_info:
        raise HTTPException(status_code=400, detail="Invalid repository path")
    
    if request.base_branch not in repo_info.branches:
        raise HTTPException(status_code=400, detail=f"Branch '{request.base_branch}' not found")
    
    # Start workflow in background
    background_tasks.add_task(run_workflow_background, request)
    
    return {
        "message": "Workflow started",
        "repo_path": request.repo_path,
        "branch": request.base_branch,
        "task": request.task
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete/terminate a session - now archives the session instead of just marking as terminated."""
    try:
        # Use the same archive functionality for both terminate and archive
        success = WorkflowOrchestrator.archive_session(session_id, cleanup_branch=True)
        
        if success:
            # Broadcast update to clients - use archived instead of terminated
            message = json.dumps({
                "type": "session_archived",
                "session_id": session_id
            })
            await manager.broadcast(message)
            
            return {"message": "Session archived successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to archive session")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error archiving session: {str(e)}")


@app.post("/api/sessions/{session_id}/archive")
async def archive_session(session_id: str, cleanup_branch: bool = True):
    """Archive a session and clean up all associated resources."""
    try:
        success = WorkflowOrchestrator.archive_session(session_id, cleanup_branch)
        
        if success:
            # Broadcast update to clients
            message = json.dumps({
                "type": "session_archived",
                "session_id": session_id
            })
            await manager.broadcast(message)
            
            return {"message": "Session archived successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to archive session")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error archiving session: {str(e)}")


@app.get("/api/sessions/{session_id}/transcripts", response_model=TranscriptResponse)
async def get_transcripts(session_id: str):
    """Get transcripts for a session."""
    transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
    
    if not transcript_dir.exists():
        raise HTTPException(status_code=404, detail="Transcripts not found")
    
    implementer_transcript = ""
    reviewer_transcript = ""
    
    implementer_file = transcript_dir / "implementer.md"
    if implementer_file.exists():
        implementer_transcript = implementer_file.read_text()
    
    reviewer_file = transcript_dir / "reviewer.md"
    if reviewer_file.exists():
        reviewer_transcript = reviewer_file.read_text()
    
    return TranscriptResponse(
        implementer=implementer_transcript,
        reviewer=reviewer_transcript
    )


@app.get("/api/sessions/{session_id}/conversation", response_model=ConversationResponse)
async def get_conversation(session_id: str):
    """Get unified conversation for a session."""
    transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
    
    if not transcript_dir.exists():
        raise HTTPException(status_code=404, detail="Transcripts not found")
    
    all_entries = []
    
    # Parse implementer transcript
    implementer_file = transcript_dir / "implementer.md"
    if implementer_file.exists():
        implementer_content = implementer_file.read_text()
        implementer_entries = parse_transcript_entries(implementer_content, "implementer")
        all_entries.extend(implementer_entries)
    
    # Parse implementer feedback transcript (for iteration loops)
    implementer_feedback_file = transcript_dir / "implementer_feedback.md"
    if implementer_feedback_file.exists():
        implementer_feedback_content = implementer_feedback_file.read_text()
        implementer_feedback_entries = parse_transcript_entries(implementer_feedback_content, "implementer")
        all_entries.extend(implementer_feedback_entries)
    
    # Parse reviewer transcript
    reviewer_file = transcript_dir / "reviewer.md"
    if reviewer_file.exists():
        reviewer_content = reviewer_file.read_text()
        reviewer_entries = parse_transcript_entries(reviewer_content, "reviewer")
        all_entries.extend(reviewer_entries)
    
    # Sort by timestamp
    all_entries.sort(key=lambda x: x.timestamp)
    
    return ConversationResponse(conversation=all_entries)


@app.get("/api/sessions/{session_id}/diff")
async def get_session_diff(session_id: str):
    """Get git diff for a session."""
    sessions = load_sessions()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    # Use workspace repo if available, otherwise fall back to original repo
    workspace_repo_path = session_data.get("workspace_repo_path")
    repo_path = workspace_repo_path or session_data.get("repo_path")
    base_branch = session_data.get("base_branch")
    
    if not repo_path or not base_branch:
        raise HTTPException(status_code=400, detail="Repository path or base branch not available")
    
    try:
        repo = Repo(repo_path)
        # Branch created by workflow template as "wizardry-{session_id}"
        workflow_branch = f"wizardry-{session_id}"
        
        # Check if workflow branch exists
        branch_names = [b.name for b in repo.branches]
        
        if workflow_branch in branch_names:
            diff = repo.git.diff(base_branch, workflow_branch)
        else:
            diff = repo.git.diff(base_branch)
        
        return {"diff": diff}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting diff: {str(e)}")


@app.get("/api/repos")
async def discover_repos(search_path: str = "."):
    """Discover git repositories."""
    repos = find_git_repos(search_path, max_depth=2)
    return repos


@app.get("/api/repos/info")
async def get_repo_info_endpoint(repo_path: str):
    """Get information about a specific repository."""
    repo_info = get_repo_info(repo_path)
    if not repo_info:
        raise HTTPException(status_code=400, detail="Invalid repository path")
    return repo_info


@app.get("/api/sessions/{session_id}/test-plan", response_model=TestPlanResponse)
async def get_test_plan(session_id: str):
    """Get test plan for a session."""
    # Check if session exists
    sessions = load_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Look for test plan file
    test_plan_file = Path(f"/tmp/wizardry-sessions/{session_id}/test_plan.md")
    
    if not test_plan_file.exists():
        raise HTTPException(status_code=404, detail="Test plan not found")
    
    try:
        test_plan_content = test_plan_file.read_text()
        
        # Try to extract structured data from test planner transcript
        transcript_file = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts/test_planner.md")
        test_plan_data = {
            "feature_name": "Feature Test Plan",
            "implementation_summary": "Test plan generated for implementation",
            "test_complexity": "moderate",
            "estimated_test_time": "15 minutes",
            "requires_data_setup": False,
            "confidence": 8,
            "test_plan_content": test_plan_content,
            "test_plan_generated": True
        }
        
        if transcript_file.exists():
            transcript_content = transcript_file.read_text()
            
            # Try to extract JSON data from transcript
            import re
            json_match = re.search(r'```json:testplan\s*\n(.*?)\n```', transcript_content, re.DOTALL)
            if json_match:
                try:
                    import json
                    extracted_data = json.loads(json_match.group(1))
                    test_plan_data.update(extracted_data)
                except Exception:
                    pass  # Use defaults if parsing fails
        
        return TestPlanResponse(**test_plan_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading test plan: {str(e)}")


@app.post("/api/broadcast/status-update")
async def broadcast_status_update(request: dict):
    """Broadcast status update to all connected WebSocket clients."""
    try:
        message = json.dumps({
            "type": "status_updated",
            "session_id": request.get("session_id"),
            "status": request.get("status")
        })
        await manager.broadcast(message)
        return {"message": "Status update broadcasted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error broadcasting status update: {str(e)}")


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back for now (can be used for client commands later)
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve static files (for production)
# In development, Next.js will handle this
if os.environ.get("ENV") == "production":
    app.mount("/", StaticFiles(directory="../frontend/out", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)