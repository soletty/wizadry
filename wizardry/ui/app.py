"""Main Streamlit application for Wizardry UI."""

import streamlit as st
from pathlib import Path
import sys

# Add the parent directory to sys.path so we can import wizardry modules
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from wizardry.ui.components.session_form import render_session_form
from wizardry.ui.components.session_list import render_session_list, render_session_stats
from wizardry.ui.components.session_detail import render_session_detail
from wizardry.ui.utils import load_sessions


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Wizardry - AI Agent Orchestrator",
        page_icon="🧙‍♂️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': "Wizardry - Multi-agent workflow orchestrator using Claude Code SDK"
        }
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    
    .status-in-progress {
        color: #ff9800;
    }
    
    .status-completed {
        color: #4caf50;
    }
    
    .status-failed {
        color: #f44336;
    }
    
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🧙‍♂️ Wizardry")
        st.write("AI Agent Orchestrator")
        st.divider()
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Dashboard", "➕ New Session", "📋 Sessions", "⚙️ Settings"],
            index=0
        )
        
        st.divider()
        
        # Quick stats
        render_sidebar_stats()
        
        st.divider()
        
        # Quick actions
        render_sidebar_actions()
    
    # Main content area
    if page == "🏠 Dashboard":
        render_dashboard()
    elif page == "➕ New Session":
        render_new_session_page()
    elif page == "📋 Sessions":
        render_sessions_page()
    elif page == "⚙️ Settings":
        render_settings_page()


def render_sidebar_stats():
    """Render quick statistics in the sidebar."""
    st.subheader("Quick Stats")
    
    sessions = load_sessions()
    
    if sessions:
        # Count by status
        status_counts = {}
        for session_data in sessions.values():
            status = session_data.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total = len(sessions)
        active = status_counts.get("in_progress", 0)
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        
        st.metric("Total Sessions", total)
        st.metric("🟡 Active", active)
        st.metric("🟢 Completed", completed)
        if failed > 0:
            st.metric("🔴 Failed", failed)
    else:
        st.info("No sessions yet")


def render_sidebar_actions():
    """Render quick actions in the sidebar."""
    st.subheader("Quick Actions")
    
    if st.button("🔄 Refresh All", use_container_width=True):
        st.rerun()
    
    if st.button("📊 View All Sessions", use_container_width=True):
        st.session_state.page = "📋 Sessions"
        st.rerun()
    
    if st.button("➕ New Workflow", use_container_width=True, type="primary"):
        st.session_state.page = "➕ New Session"
        st.rerun()


def render_dashboard():
    """Render the main dashboard page."""
    st.markdown('<h1 class="main-header">🧙‍♂️ Wizardry Dashboard</h1>', unsafe_allow_html=True)
    
    # Welcome message
    st.write("""
    Welcome to Wizardry - your AI-powered code implementation assistant! 
    
    Wizardry orchestrates specialized Claude Code agents to automatically implement features, 
    fix bugs, and create pull requests in your repositories.
    """)
    
    # Quick overview
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 Session Overview")
        render_session_stats()
        
        # Recent sessions
        st.subheader("🕒 Recent Sessions")
        sessions = load_sessions()
        
        if sessions:
            # Sort by creation time and take the 3 most recent
            recent_sessions = sorted(
                sessions.items(),
                key=lambda x: x[1].get("created_at", ""),
                reverse=True
            )[:3]
            
            for session_id, session_data in recent_sessions:
                with st.container():
                    col_a, col_b, col_c = st.columns([3, 2, 1])
                    
                    with col_a:
                        task = session_data.get("task", "Unknown task")
                        st.write(f"**{task[:50]}{'...' if len(task) > 50 else ''}**")
                    
                    with col_b:
                        status = session_data.get("status", "unknown")
                        icon = "🟡" if status == "in_progress" else "🟢" if status == "completed" else "🔴" if status == "failed" else "⚫"
                        st.write(f"{icon} {status.title()}")
                    
                    with col_c:
                        if st.button("View", key=f"view_{session_id}"):
                            st.session_state.selected_session = session_id
                            st.session_state.page = "📋 Sessions"
                            st.rerun()
                
                st.divider()
        else:
            st.info("No sessions yet. Create your first workflow!")
    
    with col2:
        st.subheader("🚀 Quick Start")
        
        st.write("**Get started in 3 steps:**")
        st.write("1. 📁 Choose your repository")
        st.write("2. 📝 Describe your task")
        st.write("3. 🚀 Let the agents work!")
        
        if st.button("Start New Workflow", type="primary", use_container_width=True):
            st.session_state.page = "➕ New Session"
            st.rerun()
        
        st.divider()
        
        st.subheader("💡 Tips")
        st.info("""
        **Write clear task descriptions:**
        - Be specific about what you want
        - Mention the feature/bug clearly
        - Include any constraints
        
        **Example:** "Add email validation to the user registration form with proper error messages"
        """)


def render_new_session_page():
    """Render the new session creation page."""
    render_session_form()


def render_sessions_page():
    """Render the sessions management page."""
    # Check if we should show a specific session
    selected_session = st.session_state.get("selected_session")
    
    if selected_session:
        # Show session detail view
        if st.button("← Back to Sessions List"):
            del st.session_state.selected_session
            st.rerun()
        
        render_session_detail(selected_session)
    else:
        # Show sessions list
        render_session_list()


def render_settings_page():
    """Render the settings/configuration page."""
    st.header("⚙️ Settings")
    
    st.subheader("Application Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**UI Preferences**")
        
        auto_refresh = st.checkbox(
            "Auto-refresh sessions", 
            value=True,
            help="Automatically refresh session data every few seconds"
        )
        
        show_completed = st.checkbox(
            "Show completed sessions by default",
            value=False,
            help="Include completed sessions in the main sessions list"
        )
        
        max_transcript_lines = st.slider(
            "Max transcript lines to display",
            min_value=20,
            max_value=200,
            value=100,
            help="Maximum number of lines to show in transcript previews"
        )
    
    with col2:
        st.write("**Workflow Defaults**")
        
        default_max_iterations = st.slider(
            "Default max review iterations",
            min_value=1,
            max_value=5,
            value=2,
            help="Default maximum number of review/fix cycles"
        )
        
        keep_branches = st.checkbox(
            "Keep workflow branches by default",
            value=False,
            help="Don't delete workflow branches after completion"
        )
    
    st.divider()
    
    st.subheader("🧹 Maintenance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🧹 Cleanup Old Sessions"):
            st.info("This would cleanup sessions older than 7 days")
    
    with col2:
        if st.button("📊 Export Session Data"):
            st.info("This would export session data to CSV")
    
    with col3:
        if st.button("🔄 Reset All Settings"):
            st.warning("This would reset all settings to defaults")
    
    st.divider()
    
    st.subheader("ℹ️ About")
    
    st.write("""
    **Wizardry** - Multi-agent workflow orchestrator
    
    - **Version**: 1.0.0
    - **Framework**: Streamlit
    - **Backend**: Claude Code SDK
    - **Session Storage**: `/tmp/wizardry-sessions/`
    
    Wizardry uses specialized AI agents to automatically implement code changes, 
    review them for quality, and create pull requests.
    """)


if __name__ == "__main__":
    main()