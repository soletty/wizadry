"""Session creation form component."""

import asyncio
from pathlib import Path
from typing import Optional

import streamlit as st
from ..utils import find_git_repos, get_repo_info, is_repo_setup_for_wizardry, setup_repo_for_wizardry
from ...orchestrator import run_orchestrator


def render_session_form():
    """Render the new session creation form."""
    st.header("🧙‍♂️ Create New Workflow")
    
    with st.form("new_session_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Repository selection
            st.subheader("Repository")
            
            # Option 1: Browse for directory
            repo_path = st.text_input(
                "Repository Path", 
                placeholder="/path/to/your/repo",
                help="Enter the path to your git repository"
            )
            
            # Option 2: Quick select from common locations
            st.write("**Or select from detected repositories:**")
            
            # Find repos in common locations
            search_locations = [
                str(Path.home() / "Documents"),
                str(Path.home() / "Projects"), 
                str(Path.home() / "dev"),
                str(Path.home()),
                "."
            ]
            
            detected_repos = []
            for location in search_locations:
                if Path(location).exists():
                    repos = find_git_repos(location, max_depth=2)
                    detected_repos.extend(repos)
            
            if detected_repos:
                repo_options = [f"{repo['path']} ({len(repo['branches'])} branches)" 
                              for repo in detected_repos]
                
                selected_repo_index = st.selectbox(
                    "Detected Repositories",
                    options=range(len(repo_options)),
                    format_func=lambda i: repo_options[i] if i < len(repo_options) else "",
                    index=None,
                    help="Select a repository from detected git repos"
                )
                
                if selected_repo_index is not None:
                    repo_path = detected_repos[selected_repo_index]["path"]
            
            # Task description
            st.subheader("Task")
            task = st.text_area(
                "Task Description",
                placeholder="Describe what you want the agents to implement...\n\nExamples:\n- Fix the login validation bug\n- Add user authentication system\n- Implement email notifications\n- Refactor the database layer",
                height=120,
                help="Be specific about what you want implemented. The more detailed, the better the result."
            )
        
        with col2:
            # Branch and options
            st.subheader("Configuration")
            
            # Get repo info for branch selection
            repo_info = None
            if repo_path:
                repo_info = get_repo_info(repo_path)
            
            if repo_info:
                # Show repo status
                st.success(f"✅ Valid Git Repository")
                st.info(f"**Current Branch**: {repo_info['current_branch']}")
                if not repo_info['is_clean']:
                    st.warning("⚠️ Repository has uncommitted changes")
                
                # Branch selection
                branches = repo_info["branches"]
                current_branch = repo_info["current_branch"]
                
                if current_branch in branches:
                    default_index = branches.index(current_branch)
                else:
                    default_index = 0
                
                base_branch = st.selectbox(
                    "Base Branch",
                    options=branches,
                    index=default_index,
                    help="Branch to create the workflow from"
                )
                
                # Wizardry setup check
                is_setup = is_repo_setup_for_wizardry(repo_path)
                if not is_setup:
                    st.warning("⚠️ Repository not setup for Wizardry")
                    if st.button("🔧 Setup Repository", type="secondary"):
                        with st.spinner("Setting up repository..."):
                            if setup_repo_for_wizardry(repo_path):
                                st.success("✅ Repository setup complete!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to setup repository")
                else:
                    st.success("✅ Repository ready for Wizardry")
            
            elif repo_path:
                st.error("❌ Invalid repository path")
            
            # Advanced options
            st.subheader("Options")
            
            no_cleanup = st.checkbox(
                "Keep workflow branch",
                help="Don't delete the workflow branch after completion"
            )
            
            max_iterations = st.slider(
                "Max Review Iterations",
                min_value=1,
                max_value=5,
                value=2,
                help="Maximum number of review/fix cycles"
            )
        
        # Submit button
        submitted = st.form_submit_button(
            "🚀 Start Workflow",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validation
            if not repo_path:
                st.error("Please select a repository")
                return
            
            if not task.strip():
                st.error("Please provide a task description")
                return
            
            if not repo_info:
                st.error("Invalid repository path")
                return
            
            if not is_repo_setup_for_wizardry(repo_path):
                st.error("Repository must be setup for Wizardry first")
                return
            
            # Start the workflow
            start_workflow(repo_path, base_branch, task.strip(), no_cleanup, max_iterations)


def start_workflow(repo_path: str, branch: str, task: str, no_cleanup: bool, max_iterations: int):
    """Start a new workflow session."""
    st.info("🚀 Starting workflow...")
    
    # Create progress placeholder
    progress_container = st.container()
    
    with progress_container:
        # Show workflow details
        st.subheader("Workflow Details")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Repository**: {Path(repo_path).name}")
            st.write(f"**Branch**: {branch}")
        with col2:
            st.write(f"**No Cleanup**: {'Yes' if no_cleanup else 'No'}")
            st.write(f"**Max Iterations**: {max_iterations}")
        
        st.write(f"**Task**: {task}")
        
        # Progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Start workflow in background
        if "workflow_running" not in st.session_state:
            st.session_state.workflow_running = True
            
            status_text.text("🔧 Starting implementer agent...")
            progress_bar.progress(25)
            
            try:
                # Run the workflow
                success = asyncio.run(run_orchestrator(repo_path, branch, task))
                
                progress_bar.progress(100)
                
                if success:
                    status_text.text("✅ Workflow completed successfully!")
                    st.success("🎉 Workflow completed! Check the Sessions page for details and PR links.")
                else:
                    status_text.text("❌ Workflow failed")
                    st.error("❌ Workflow failed. Check the Sessions page for details.")
                
            except Exception as e:
                status_text.text(f"❌ Error: {e}")
                st.error(f"❌ Workflow error: {e}")
            
            finally:
                st.session_state.workflow_running = False
        
        # Auto-refresh while workflow is running
        if st.session_state.get("workflow_running", False):
            st.rerun()