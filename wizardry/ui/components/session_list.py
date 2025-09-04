"""Session list component for displaying active and completed sessions."""

import time
from pathlib import Path
from typing import Dict, Any

import streamlit as st
from ..utils import (
    load_sessions, 
    get_session_status_icon, 
    format_timestamp,
    truncate_text,
    kill_session
)


def render_session_list():
    """Render the session list page."""
    st.header("📊 Workflow Sessions")
    
    # Auto-refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=True)
    with col2:
        if st.button("🔄 Refresh Now"):
            st.rerun()
    with col3:
        show_completed = st.checkbox("Show Completed", value=False)
    
    # Load sessions
    sessions = load_sessions()
    
    if not sessions:
        st.info("🔮 No workflow sessions found. Create one using the New Session page!")
        return
    
    # Filter sessions based on preferences
    filtered_sessions = {}
    for session_id, session_data in sessions.items():
        status = session_data.get("status", "unknown")
        if show_completed or status not in ["completed", "terminated"]:
            filtered_sessions[session_id] = session_data
    
    if not filtered_sessions:
        if show_completed:
            st.info("No sessions found.")
        else:
            st.info("No active sessions. Enable 'Show Completed' to see finished workflows.")
        return
    
    # Sort sessions by creation time (newest first)
    sorted_sessions = sorted(
        filtered_sessions.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True
    )
    
    # Display sessions
    for session_id, session_data in sorted_sessions:
        render_session_card(session_id, session_data)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(0.1)  # Small delay to prevent too rapid refresh
        st.rerun()


def render_session_card(session_id: str, session_data: Dict[str, Any]):
    """Render a single session card."""
    status = session_data.get("status", "unknown")
    status_icon = get_session_status_icon(status)
    
    # Create expandable card
    with st.container():
        # Header row
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            st.write(f"**{status_icon} {truncate_text(session_data.get('task', 'Unknown task'), 60)}**")
        
        with col2:
            repo_name = Path(session_data.get("repo_path", "")).name
            st.write(f"📁 {repo_name}")
        
        with col3:
            created_at = format_timestamp(session_data.get("created_at", ""))
            st.write(f"🕒 {created_at}")
        
        with col4:
            if st.button("📋", key=f"details_{session_id}", help="View Details"):
                st.session_state.selected_session = session_id
                st.switch_page("pages/Session_Details.py")
        
        # Expandable details
        with st.expander(f"Details - {session_id}", expanded=False):
            render_session_details(session_id, session_data)
        
        st.divider()


def render_session_details(session_id: str, session_data: Dict[str, Any]):
    """Render detailed session information."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Session Information**")
        st.write(f"**ID**: `{session_id}`")
        st.write(f"**Status**: {get_session_status_icon(session_data.get('status'))} {session_data.get('status', 'unknown').title()}")
        st.write(f"**Base Branch**: {session_data.get('base_branch', 'unknown')}")
        st.write(f"**Repository**: {session_data.get('repo_path', 'unknown')}")
        
        # Show timestamps
        created_at = session_data.get("created_at")
        if created_at:
            st.write(f"**Created**: {format_timestamp(created_at)}")
        
        terminated_at = session_data.get("terminated_at")
        if terminated_at:
            st.write(f"**Terminated**: {format_timestamp(terminated_at)}")
    
    with col2:
        st.write("**Task Description**")
        task = session_data.get("task", "No description available")
        st.write(task)
        
        # Action buttons
        st.write("**Actions**")
        
        button_col1, button_col2, button_col3 = st.columns(3)
        
        with button_col1:
            if st.button("📋 Details", key=f"detail_btn_{session_id}"):
                st.session_state.selected_session = session_id
                st.switch_page("pages/Session_Details.py")
        
        with button_col2:
            status = session_data.get("status", "")
            if status in ["in_progress", "failed"]:
                if st.button("🗑️ Kill", key=f"kill_btn_{session_id}", type="secondary"):
                    with st.spinner("Terminating session..."):
                        if kill_session(session_id):
                            st.success(f"✅ Session {session_id} terminated")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to terminate session {session_id}")
        
        with button_col3:
            # Show workspace path if exists
            workspace_path = session_data.get("workspace_path")
            if workspace_path and Path(workspace_path).exists():
                st.write(f"**Workspace**: `{workspace_path}`")
    
    # Show progress indicators for active sessions
    status = session_data.get("status", "")
    if status == "in_progress":
        st.info("🔄 This session is currently running. Check back for updates!")
        
        # Show a simple progress indicator
        progress_container = st.container()
        with progress_container:
            st.write("**Progress Indicators**")
            
            # Check for transcript files to gauge progress
            transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
            if transcript_dir.exists():
                transcript_files = list(transcript_dir.glob("*.md"))
                
                col_a, col_b = st.columns(2)
                with col_a:
                    implementer_exists = any("implementer" in f.name for f in transcript_files)
                    st.write(f"🔧 Implementer: {'✅' if implementer_exists else '⏳'}")
                with col_b:
                    reviewer_exists = any("reviewer" in f.name for f in transcript_files)
                    st.write(f"🔍 Reviewer: {'✅' if reviewer_exists else '⏳'}")
    
    elif status == "completed":
        st.success("✅ This session completed successfully!")
        
        # Try to show PR link if available
        # This would need to be stored in session data when PR is created
        pr_url = session_data.get("pr_url")
        if pr_url:
            st.write(f"**Pull Request**: [{pr_url}]({pr_url})")
    
    elif status == "failed":
        st.error("❌ This session failed to complete.")
        st.write("Check the transcripts for error details.")
    
    elif status == "terminated":
        st.warning("⚫ This session was manually terminated.")


def render_session_stats():
    """Render session statistics."""
    sessions = load_sessions()
    
    if not sessions:
        return
    
    # Count by status
    status_counts = {}
    for session_data in sessions.values():
        status = session_data.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    st.subheader("📈 Session Statistics")
    
    cols = st.columns(len(status_counts))
    for i, (status, count) in enumerate(status_counts.items()):
        with cols[i]:
            icon = get_session_status_icon(status)
            st.metric(f"{icon} {status.title()}", count)