"""CLI interface for Wizardry agent orchestrator."""

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


def get_templates_dir() -> Path:
    """Get the templates directory path."""
    return Path(__file__).parent.parent / "templates"


def get_session_registry_path() -> Path:
    """Get the session registry path."""
    return Path("/tmp/wizardry-sessions/registry.json")


def load_sessions():
    """Load active sessions from registry."""
    registry_file = get_session_registry_path()
    if not registry_file.exists():
        return {}
    
    try:
        with open(registry_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


@click.group()
def cli():
    """Wizardry: Multi-agent workflow orchestrator for repositories."""
    pass


@cli.command()
@click.option('--repo', required=True, help='Path to target repository')
@click.option('--force', is_flag=True, help='Overwrite existing Claude Code configs')
def setup(repo: str, force: bool):
    """Setup a repository for Wizardry agent workflows."""
    repo_path = Path(repo).resolve()
    
    if not repo_path.exists():
        rprint(f"[red]Error: Repository path does not exist: {repo_path}[/red]")
        sys.exit(1)
    
    if not (repo_path / ".git").exists():
        rprint(f"[red]Error: {repo_path} is not a git repository[/red]")
        sys.exit(1)
    
    claude_dir = repo_path / ".claude"
    
    # Check if already setup
    if claude_dir.exists() and not force:
        rprint(f"[yellow]Warning: {repo_path} already has Claude Code configs[/yellow]")
        rprint("Use --force to overwrite, or run 'wizardry status' to check setup")
        sys.exit(1)
    
    # Copy templates
    templates_dir = get_templates_dir() / ".claude"
    
    try:
        if claude_dir.exists():
            shutil.rmtree(claude_dir)
        
        shutil.copytree(templates_dir, claude_dir)
        rprint(f"[green]✅ Successfully setup {repo_path} for Wizardry workflows[/green]")
        rprint(f"[dim]Configs copied to: {claude_dir}[/dim]")
        rprint("")
        rprint("[bold]Next steps:[/bold]")
        rprint("1. cd " + str(repo_path))
        rprint("2. claude")
        rprint("3. /workflow --branch main --task \"Your task description\"")
        
    except Exception as e:
        rprint(f"[red]Error setting up repository: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--repo', help='Path to check (defaults to current directory)')
def status(repo: Optional[str]):
    """Check if a repository is setup for Wizardry workflows."""
    repo_path = Path(repo or ".").resolve()
    claude_dir = repo_path / ".claude"
    
    if not claude_dir.exists():
        rprint(f"[red]❌ {repo_path} is not setup for Wizardry[/red]")
        rprint("Run 'wizardry setup --repo .' to enable workflows")
        sys.exit(1)
    
    # Check for required files
    required_files = [
        ".claude/agents/implementer.json",
        ".claude/agents/reviewer.json", 
        ".claude/settings.json",
        ".claude/commands/workflow.md",
        ".claude/hooks/post_tool.sh"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (repo_path / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        rprint(f"[yellow]⚠️  {repo_path} has incomplete Wizardry setup[/yellow]")
        rprint("Missing files:")
        for file_path in missing_files:
            rprint(f"  - {file_path}")
        rprint("Run 'wizardry setup --repo . --force' to fix")
    else:
        rprint(f"[green]✅ {repo_path} is ready for Wizardry workflows[/green]")
        
        # Show active workflows
        workflows_dir = repo_path / ".wizardry"
        if workflows_dir.exists() and (workflows_dir / "current_workflow.json").exists():
            with open(workflows_dir / "current_workflow.json", 'r') as f:
                workflow = json.load(f)
            rprint(f"[blue]🔄 Active workflow: {workflow['workflow_id']}[/blue]")
            rprint(f"[dim]Task: {workflow['task']}[/dim]")
            rprint(f"[dim]Status: {workflow['status']}[/dim]")


@cli.command()
def sessions():
    """List all active Wizardry sessions across repos."""
    sessions = load_sessions()
    
    if not sessions:
        rprint("[dim]No active Wizardry sessions[/dim]")
        return
    
    table = Table(title="Active Wizardry Sessions")
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Repository", style="green")
    table.add_column("Task", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Started", style="dim")
    
    for session_id, session_data in sessions.items():
        if session_data.get("status") not in ["completed", "failed", "terminated"]:
            table.add_row(
                session_id,
                str(Path(session_data["repo_path"]).name),
                session_data["task"][:50] + ("..." if len(session_data["task"]) > 50 else ""),
                session_data["status"],
                session_data["created_at"][:16]
            )
    
    console.print(table)


@cli.command()
@click.argument('session_id')
def transcripts(session_id: str):
    """Show transcripts for a workflow session."""
    transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
    
    if not transcript_dir.exists():
        rprint(f"[red]Error: No transcripts found for session {session_id}[/red]")
        sys.exit(1)
    
    rprint(f"[bold]Transcripts for session: {session_id}[/bold]")
    
    for transcript_file in transcript_dir.glob("*.md"):
        rprint(f"\n[green]📝 {transcript_file.name}[/green]")
        rprint("[dim]" + "="*50 + "[/dim]")
        
        try:
            content = transcript_file.read_text()
            # Show last 20 lines to avoid overwhelming output
            lines = content.split('\n')
            if len(lines) > 20:
                rprint("[dim]... (showing last 20 lines) ...[/dim]")
                content = '\n'.join(lines[-20:])
            
            rprint(content)
        except Exception as e:
            rprint(f"[red]Error reading {transcript_file}: {e}[/red]")


@cli.command()
@click.argument('session_id')
def kill(session_id: str):
    """Terminate a workflow session and cleanup workspace."""
    sessions = load_sessions()
    
    if session_id not in sessions:
        rprint(f"[red]Error: Session {session_id} not found[/red]")
        sys.exit(1)
    
    # Archive transcripts
    session_data = sessions[session_id]
    transcript_dir = Path(f"/tmp/wizardry-sessions/{session_id}/transcripts")
    archive_dir = Path(f"/tmp/wizardry-sessions/archived/{session_id}")
    
    if transcript_dir.exists():
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(transcript_dir, archive_dir / "transcripts", dirs_exist_ok=True)
        rprint(f"[blue]📦 Transcripts archived to: {archive_dir}[/blue]")
    
    # Cleanup workspace
    workspace_dir = Path(f"/tmp/wizardry-sessions/{session_id}")
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)
    
    # Update registry
    sessions[session_id]["status"] = "terminated"
    with open(get_session_registry_path(), 'w') as f:
        json.dump(sessions, f, indent=2)
    
    rprint(f"[green]✅ Session {session_id} terminated[/green]")


@cli.command()
@click.option('--port', default=3005, help='Port to run the frontend on (default: 3005)')
@click.option('--api-port', default=8001, help='Port to run the API on (default: 8001)')
def ui(port: int, api_port: int):
    """Launch the Wizardry web UI (TypeScript/Next.js)."""
    import os
    import subprocess
    import threading
    import time
    
    # Get the UI directory
    ui_dir = Path(__file__).parent.parent / "ui"
    
    if not ui_dir.exists():
        rprint(f"[red]Error: UI directory not found at {ui_dir}[/red]")
        rprint("The web UI may not be installed correctly.")
        sys.exit(1)
    
    backend_dir = ui_dir / "backend"
    frontend_dir = ui_dir / "frontend"
    
    if not backend_dir.exists() or not frontend_dir.exists():
        rprint(f"[red]Error: UI components not found[/red]")
        rprint("Run 'cd wizardry/ui/frontend && npm install' to setup the frontend")
        sys.exit(1)
    
    rprint(f"[bold]🧙‍♂️ Launching Wizardry UI...[/bold]")
    rprint(f"[dim]API Server: http://localhost:{api_port}[/dim]")
    rprint(f"[dim]Web Interface: http://localhost:{port}[/dim]")
    rprint(f"[dim]Press Ctrl+C to stop both servers[/dim]")
    rprint("")
    
    def start_backend():
        """Start the FastAPI backend server."""
        try:
            rprint("[blue]🔧 Starting API server...[/blue]")
            # Find the venv python and uvicorn
            import sys
            venv_python = sys.executable
            venv_dir = Path(venv_python).parent
            uvicorn_path = venv_dir / "uvicorn"
            
            if uvicorn_path.exists():
                subprocess.run([
                    str(uvicorn_path), "main:app",
                    "--host", "0.0.0.0", 
                    "--port", str(api_port),
                    "--reload"
                ], cwd=backend_dir)
            else:
                # Fallback: use python -m uvicorn
                subprocess.run([
                    venv_python, "-m", "uvicorn", "main:app",
                    "--host", "0.0.0.0",
                    "--port", str(api_port), 
                    "--reload"
                ], cwd=backend_dir)
        except Exception as e:
            rprint(f"[red]❌ Backend error: {e}[/red]")
    
    def start_frontend():
        """Start the Next.js frontend server."""
        try:
            time.sleep(2)  # Give backend time to start
            rprint("[blue]🎨 Starting frontend server...[/blue]")
            
            # Set environment variables for API connection
            env = os.environ.copy()
            env['NEXT_PUBLIC_API_URL'] = f'http://localhost:{api_port}/api'
            env['NEXT_PUBLIC_WS_URL'] = f'ws://localhost:{api_port}/api/ws'
            
            subprocess.run([
                "npm", "run", "dev", "--", "--port", str(port)
            ], cwd=frontend_dir, env=env)
        except Exception as e:
            rprint(f"[red]❌ Frontend error: {e}[/red]")
    
    try:
        # Check if required dependencies are available
        try:
            subprocess.run(["uvicorn", "--version"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            rprint("[red]❌ uvicorn not found. Please install it:[/red]")
            rprint("pip install uvicorn[standard]")
            sys.exit(1)
        
        # Check if npm is available
        try:
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            rprint("[red]❌ npm not found. Please install Node.js first.[/red]")
            sys.exit(1)
        
        # Start backend in a separate thread
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        
        # Start frontend in main thread (so Ctrl+C works properly)
        start_frontend()
        
    except KeyboardInterrupt:
        rprint("\n[green]✅ Wizardry UI stopped[/green]")
    except Exception as e:
        rprint(f"[red]❌ Error launching UI: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--repo', default='.', help='Path to repository (defaults to current directory)')
@click.option('--branch', required=True, help='Base branch to work from')
@click.option('--task', required=True, help='Task description for agents to implement')
@click.option('--no-cleanup', is_flag=True, help='Keep workflow branch after completion')
@click.option('--auto-setup', is_flag=True, help='Automatically setup repository if not configured')
def run(repo: str, branch: str, task: str, no_cleanup: bool, auto_setup: bool):
    """Run a complete multi-agent workflow on a repository."""
    import asyncio
    from ..orchestrator import run_orchestrator
    
    repo_path = Path(repo).resolve()
    
    # Validate inputs
    if not repo_path.exists():
        rprint(f"[red]Error: Repository path does not exist: {repo_path}[/red]")
        sys.exit(1)
    
    if not (repo_path / ".git").exists():
        rprint(f"[red]Error: {repo_path} is not a git repository[/red]")
        sys.exit(1)
    
    # Auto-setup if needed
    claude_dir = repo_path / ".claude"
    if not claude_dir.exists():
        if auto_setup:
            rprint(f"[yellow]⚙️ Repository not setup for Wizardry, auto-setting up...[/yellow]")
            try:
                # Copy templates
                templates_dir = get_templates_dir() / ".claude"
                shutil.copytree(templates_dir, claude_dir)
                rprint(f"[green]✅ Repository setup completed[/green]")
            except Exception as e:
                rprint(f"[red]❌ Auto-setup failed: {e}[/red]")
                rprint("Run 'wizardry setup --repo .' manually")
                sys.exit(1)
        else:
            rprint(f"[red]Error: {repo_path} is not setup for Wizardry[/red]")
            rprint("Options:")
            rprint("  1. Run: wizardry setup --repo .")
            rprint("  2. Use: wizardry run --auto-setup --branch ... --task ...")
            sys.exit(1)
    
    # Validate branch exists
    from git import Repo, InvalidGitRepositoryError
    try:
        git_repo = Repo(repo_path)
        branch_names = [b.name for b in git_repo.branches]
        remote_branches = []
        try:
            for remote in git_repo.remotes:
                remote_branches.extend([ref.name.split('/')[-1] for ref in remote.refs])
        except:
            pass
        
        all_branches = set(branch_names + remote_branches)
        if branch not in all_branches:
            rprint(f"[red]Error: Branch '{branch}' not found[/red]")
            rprint("[dim]Available branches:[/dim]")
            for b in sorted(all_branches):
                rprint(f"  - {b}")
            sys.exit(1)
    except InvalidGitRepositoryError:
        rprint(f"[red]Error: {repo_path} is not a valid git repository[/red]")
        sys.exit(1)
    
    rprint(f"[bold]🚀 Starting Wizardry workflow[/bold]")
    rprint(f"[dim]Repository: {repo_path}[/dim]")
    rprint(f"[dim]Branch: {branch}[/dim]")
    rprint(f"[dim]Task: {task}[/dim]")
    rprint("")
    
    # Run the orchestrated workflow
    try:
        success = asyncio.run(run_orchestrator(str(repo_path), branch, task))
        
        if success:
            rprint("[green]🎉 Workflow completed successfully![/green]")
            if not no_cleanup:
                rprint("[dim]Use --no-cleanup to keep workflow branch[/dim]")
        else:
            rprint("[red]❌ Workflow failed[/red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        rprint("\n[yellow]⚠️ Workflow interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        rprint(f"[red]❌ Workflow error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()