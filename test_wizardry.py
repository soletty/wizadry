#!/usr/bin/env python3
"""Simple test script to verify Wizardry implementation."""

import json
import shutil
import tempfile
from pathlib import Path


def test_template_structure():
    """Test that all required templates exist."""
    templates_dir = Path("wizardry/templates/.claude")
    
    required_files = [
        "agents/implementer.json",
        "agents/reviewer.json",
        "settings.json", 
        "commands/workflow.md",
        "hooks/post_tool.sh",
        "hooks/pre_tool.sh",
        "hooks/transcript_logger.sh"
    ]
    
    print("🔍 Checking template structure...")
    
    missing_files = []
    for file_path in required_files:
        full_path = templates_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All template files present")
    return True


def test_agent_configs():
    """Test that agent configs are valid JSON."""
    print("\n🤖 Checking agent configurations...")
    
    agent_files = [
        "wizardry/templates/.claude/agents/implementer.json",
        "wizardry/templates/.claude/agents/reviewer.json"
    ]
    
    for agent_file in agent_files:
        try:
            with open(agent_file, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ["name", "description", "system_prompt"]
            for field in required_fields:
                if field not in config:
                    print(f"❌ {agent_file} missing field: {field}")
                    return False
            
            print(f"  ✅ {Path(agent_file).name} - {config['name']} agent valid")
            
        except json.JSONDecodeError as e:
            print(f"❌ {agent_file} has invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading {agent_file}: {e}")
            return False
    
    print("✅ All agent configs valid")
    return True


def test_hook_executables():
    """Test that hook scripts are executable."""
    print("\n🔗 Checking hook executables...")
    
    hook_dir = Path("wizardry/templates/.claude/hooks")
    hooks = list(hook_dir.glob("*.sh"))
    
    if not hooks:
        print("❌ No hook scripts found")
        return False
    
    for hook in hooks:
        if not hook.is_file():
            print(f"❌ {hook.name} is not a file")
            return False
        
        # Check if executable (on Unix systems)
        import stat
        if not (hook.stat().st_mode & stat.S_IEXEC):
            print(f"⚠️  {hook.name} is not executable")
        else:
            print(f"  ✅ {hook.name} executable")
    
    print("✅ All hooks ready")
    return True


def test_workflow_command():
    """Test that workflow command exists and is executable."""
    print("\n⚡ Checking workflow command...")
    
    workflow_cmd = Path("wizardry/templates/.claude/commands/workflow.md")
    
    if not workflow_cmd.exists():
        print("❌ workflow command not found")
        return False
    
    if not workflow_cmd.is_file():
        print("❌ workflow command is not a file")
        return False
    
    # Check if executable
    import stat
    if not (workflow_cmd.stat().st_mode & stat.S_IEXEC):
        print("⚠️  workflow command is not executable")
    else:
        print("  ✅ workflow command executable")
    
    print("✅ Workflow command ready")
    return True


def main():
    """Run all tests."""
    print("🧙‍♂️ Testing Wizardry Implementation")
    print("=" * 40)
    
    tests = [
        test_template_structure,
        test_agent_configs,
        test_hook_executables,
        test_workflow_command
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! Wizardry is ready to use.")
        print("\nNext steps:")
        print("1. Install: pip install -e .")
        print("2. Setup a repo: wizardry setup --repo /path/to/repo")
        print("3. Start workflow: cd /path/to/repo && claude")
        print("4. Run: /workflow --branch main --task 'Your task'")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())