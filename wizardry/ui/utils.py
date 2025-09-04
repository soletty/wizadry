"""Utility functions for the Streamlit UI."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import streamlit as st
from git import Repo, InvalidGitRepositoryError


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


def get_repo_info(repo_path: str) -> Optional[Dict[str, Any]]:
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
        
        return {
            "path": repo_path,
            "branches": branches,
            "current_branch": current_branch,
            "is_clean": not repo.is_dirty(),
            "remote_url": get_remote_url(repo)
        }
    except InvalidGitRepositoryError:
        return None


def get_remote_url(repo: Repo) -> Optional[str]:
    """Get remote URL for the repository."""
    try:
        if repo.remotes:
            return repo.remotes.origin.url
    except Exception:
        pass
    return None


def find_git_repos(search_path: str = ".", max_depth: int = 3) -> List[Dict[str, Any]]:
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
        if repo["path"] not in seen_paths:
            seen_paths.add(repo["path"])
            unique_repos.append(repo)
    
    return unique_repos


def get_session_transcripts(session_id: str) -> Dict[str, str]:
    """Get transcripts for a session."""
    transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
    transcripts = {}
    
    if transcript_dir.exists():
        for transcript_file in transcript_dir.glob("*.md"):
            try:
                content = transcript_file.read_text()
                transcripts[transcript_file.stem] = content
            except Exception:
                transcripts[transcript_file.stem] = "Error loading transcript"
    
    return transcripts


def get_git_diff(repo_path: str, base_branch: str, target_branch: str = None) -> str:
    """Get git diff between branches."""
    try:
        repo = Repo(repo_path)
        if target_branch:
            return repo.git.diff(base_branch, target_branch)
        else:
            # Compare current working tree with base branch
            return repo.git.diff(base_branch)
    except Exception as e:
        return f"Error getting diff: {e}"


def kill_session(session_id: str) -> bool:
    """Kill and cleanup a workflow session."""
    try:
        sessions = load_sessions()
        
        if session_id not in sessions:
            return False
        
        session_data = sessions[session_id]
        
        # Archive transcripts
        transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
        archive_dir = Path(f"/tmp/wizardry-sessions/archived/{session_id}")
        
        if transcript_dir.exists():
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(transcript_dir, archive_dir / "transcripts", dirs_exist_ok=True)
        
        # Cleanup workspace
        workspace_dir = Path(f"/tmp/wizardry-sessions/{session_id}")
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir, ignore_errors=True)
        
        # Update registry
        sessions[session_id]["status"] = "terminated"
        sessions[session_id]["terminated_at"] = datetime.now().isoformat()
        save_sessions(sessions)
        
        # Cleanup git branch if it exists
        try:
            repo = Repo(session_data["repo_path"])
            branch_name = f"wizardry-{session_id}"
            if branch_name in [b.name for b in repo.branches]:
                # Switch to base branch first
                repo.git.checkout(session_data["base_branch"])
                # Delete the workflow branch
                repo.git.branch('-D', branch_name)
        except Exception:
            pass  # Branch cleanup is not critical
        
        return True
    except Exception:
        return False


def is_repo_setup_for_wizardry(repo_path: str) -> bool:
    """Check if repository is setup for Wizardry."""
    claude_dir = Path(repo_path) / ".claude"
    return claude_dir.exists()


def setup_repo_for_wizardry(repo_path: str) -> bool:
    """Setup repository for Wizardry workflows."""
    try:
        # This is a simplified setup - in practice you'd copy templates
        claude_dir = Path(repo_path) / ".claude"
        claude_dir.mkdir(exist_ok=True)
        
        # Create basic setup marker
        setup_marker = claude_dir / "wizardry_setup.json"
        setup_data = {
            "setup_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        with open(setup_marker, 'w') as f:
            json.dump(setup_data, f, indent=2)
        
        return True
    except Exception:
        return False


def get_session_status_icon(status: str) -> str:
    """Get status icon for session."""
    status_icons = {
        "in_progress": "🟡",
        "completed": "🟢",
        "failed": "🔴",
        "terminated": "⚫"
    }
    return status_icons.get(status, "⚪")


def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp_str


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."