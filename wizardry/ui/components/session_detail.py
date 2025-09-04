"""Session detail component for viewing individual session information."""

from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st
from ..utils import (
    load_sessions,
    get_session_transcripts,
    get_git_diff,
    get_session_status_icon,
    format_timestamp,
    kill_session
)


def render_session_detail(session_id: str):
    """Render detailed view of a specific session."""
    sessions = load_sessions()
    
    if session_id not in sessions:
        st.error(f"Session {session_id} not found")
        return
    
    session_data = sessions[session_id]
    status = session_data.get("status", "unknown")
    status_icon = get_session_status_icon(status)
    
    # Header
    st.title(f"{status_icon} Workflow Session")
    st.caption(f"Session ID: `{session_id}`")
    
    # Session overview
    render_session_overview(session_id, session_data)
    
    # Tabbed interface for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Overview", 
        "🔧 Implementation", 
        "🔍 Review",
        "📝 Git Changes", 
        "⚙️ Actions"
    ])
    
    with tab1:
        render_overview_tab(session_id, session_data)
    
    with tab2:
        render_implementation_tab(session_id, session_data)
    
    with tab3:
        render_review_tab(session_id, session_data)
    
    with tab4:
        render_git_changes_tab(session_id, session_data)
    
    with tab5:
        render_actions_tab(session_id, session_data)


def render_session_overview(session_id: str, session_data: Dict[str, Any]):
    """Render session overview section."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Status",
            session_data.get("status", "unknown").title(),
            delta=None
        )
    
    with col2:
        repo_path = session_data.get("repo_path", "")
        repo_name = Path(repo_path).name if repo_path else "Unknown"
        st.metric("Repository", repo_name)
    
    with col3:
        branch = session_data.get("base_branch", "unknown")
        st.metric("Base Branch", branch)
    
    # Task description
    st.subheader("Task Description")
    task = session_data.get("task", "No description available")
    st.write(task)
    
    # Timeline
    st.subheader("Timeline")
    created_at = session_data.get("created_at")
    if created_at:
        st.write(f"**Created**: {format_timestamp(created_at)}")
    
    terminated_at = session_data.get("terminated_at")
    if terminated_at:
        st.write(f"**Terminated**: {format_timestamp(terminated_at)}")


def render_overview_tab(session_id: str, session_data: Dict[str, Any]):
    """Render the overview tab."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Session Details")
        
        details = {
            "Session ID": session_id,
            "Status": session_data.get("status", "unknown").title(),
            "Repository Path": session_data.get("repo_path", "unknown"),
            "Base Branch": session_data.get("base_branch", "unknown"),
            "Workspace Path": session_data.get("workspace_path", "unknown")
        }
        
        for key, value in details.items():
            st.write(f"**{key}**: `{value}`")
    
    with col2:
        st.subheader("Progress Tracking")
        
        # Check transcript availability to show progress
        transcripts = get_session_transcripts(session_id)
        
        progress_items = [
            ("🔧 Implementer Started", "implementer" in transcripts),
            ("🔍 Reviewer Started", "reviewer" in transcripts),
            ("📝 Changes Committed", check_git_changes_exist(session_data)),
            ("✅ Session Completed", session_data.get("status") == "completed")
        ]
        
        for item_name, is_done in progress_items:
            icon = "✅" if is_done else "⏳"
            st.write(f"{icon} {item_name}")
    
    # Show PR information if available
    pr_url = session_data.get("pr_url")
    if pr_url:
        st.subheader("Pull Request")
        st.success(f"✅ Pull Request created: [{pr_url}]({pr_url})")


def render_implementation_tab(session_id: str, session_data: Dict[str, Any]):
    """Render the implementation tab showing implementer transcript."""
    st.subheader("🔧 Implementer Agent")
    
    transcripts = get_session_transcripts(session_id)
    implementer_transcript = transcripts.get("implementer", "")
    
    if implementer_transcript:
        st.write("**Implementer Conversation:**")
        
        # Use expandable sections for better readability
        with st.expander("View Full Implementer Transcript", expanded=True):
            st.code(implementer_transcript, language="markdown")
        
        # Extract key information if possible
        if "```json:implementation" in implementer_transcript:
            st.subheader("Implementation Summary")
            try:
                import re
                json_match = re.search(r'```json:implementation\s*\n(.*?)\n```', implementer_transcript, re.DOTALL)
                if json_match:
                    implementation_json = json_match.group(1)
                    st.code(implementation_json, language="json")
            except Exception:
                pass
    else:
        status = session_data.get("status", "")
        if status == "in_progress":
            st.info("🔄 Implementer agent is working...")
        else:
            st.warning("⚠️ No implementer transcript found")


def render_review_tab(session_id: str, session_data: Dict[str, Any]):
    """Render the review tab showing reviewer transcript."""
    st.subheader("🔍 Reviewer Agent")
    
    transcripts = get_session_transcripts(session_id)
    reviewer_transcript = transcripts.get("reviewer", "")
    
    if reviewer_transcript:
        st.write("**Reviewer Conversation:**")
        
        with st.expander("View Full Reviewer Transcript", expanded=True):
            st.code(reviewer_transcript, language="markdown")
        
        # Extract review summary if possible
        if "```json:review" in reviewer_transcript:
            st.subheader("Review Summary")
            try:
                import re
                json_match = re.search(r'```json:review\s*\n(.*?)\n```', reviewer_transcript, re.DOTALL)
                if json_match:
                    review_json = json_match.group(1)
                    st.code(review_json, language="json")
            except Exception:
                pass
    else:
        transcripts = get_session_transcripts(session_id)
        if "implementer" in transcripts:
            status = session_data.get("status", "")
            if status == "in_progress":
                st.info("⏳ Waiting for reviewer agent to start...")
            else:
                st.warning("⚠️ No reviewer transcript found")
        else:
            st.info("⏳ Waiting for implementer to complete...")


def render_git_changes_tab(session_id: str, session_data: Dict[str, Any]):
    """Render the git changes tab showing diffs."""
    st.subheader("📝 Git Changes")
    
    repo_path = session_data.get("repo_path")
    base_branch = session_data.get("base_branch")
    
    if not repo_path or not base_branch:
        st.error("Repository path or base branch not available")
        return
    
    # Try to get the workflow branch
    workflow_branch = f"wizardry-{session_id}"
    
    try:
        from git import Repo
        repo = Repo(repo_path)
        
        # Check if workflow branch exists
        branch_names = [b.name for b in repo.branches]
        
        if workflow_branch in branch_names:
            st.info(f"Showing changes from branch: `{workflow_branch}`")
            diff = get_git_diff(repo_path, base_branch, workflow_branch)
        else:
            st.info(f"Workflow branch not found. Showing working tree changes.")
            diff = get_git_diff(repo_path, base_branch)
        
        if diff.strip():
            st.write("**Diff:**")
            st.code(diff, language="diff")
        else:
            st.info("No changes detected")
            
    except Exception as e:
        st.error(f"Error getting git diff: {e}")


def render_actions_tab(session_id: str, session_data: Dict[str, Any]):
    """Render the actions tab for session management."""
    st.subheader("⚙️ Session Actions")
    
    status = session_data.get("status", "unknown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Session Management**")
        
        if status in ["in_progress", "failed"]:
            if st.button("🗑️ Kill Session", type="secondary"):
                with st.spinner("Terminating session..."):
                    if kill_session(session_id):
                        st.success("✅ Session terminated successfully")
                        st.rerun()
                    else:
                        st.error("❌ Failed to terminate session")
        
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    with col2:
        st.write("**Quick Actions**")
        
        # Show workspace path
        workspace_path = session_data.get("workspace_path")
        if workspace_path:
            st.code(f"Workspace: {workspace_path}")
        
        # Show repository path
        repo_path = session_data.get("repo_path")
        if repo_path:
            st.code(f"Repository: {repo_path}")
    
    # Danger zone
    st.divider()
    st.subheader("⚠️ Danger Zone")
    st.warning("These actions cannot be undone!")
    
    if st.button("🗑️ Force Delete Session Data", type="secondary"):
        st.error("This would permanently delete all session data including transcripts")
        # Could implement force delete here


def check_git_changes_exist(session_data: Dict[str, Any]) -> bool:
    """Check if git changes exist for the session."""
    repo_path = session_data.get("repo_path")
    base_branch = session_data.get("base_branch")
    
    if not repo_path or not base_branch:
        return False
    
    try:
        diff = get_git_diff(repo_path, base_branch)
        return bool(diff.strip())
    except Exception:
        return False