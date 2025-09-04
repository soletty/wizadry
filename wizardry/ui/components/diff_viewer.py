"""Diff viewer component with syntax highlighting."""

import re
from typing import List, Tuple

import streamlit as st


def render_diff_viewer(diff_content: str, title: str = "Git Diff"):
    """Render a syntax-highlighted diff viewer."""
    st.subheader(title)
    
    if not diff_content.strip():
        st.info("No changes to display")
        return
    
    # Parse the diff into structured data
    diff_sections = parse_diff(diff_content)
    
    if not diff_sections:
        # Fallback to raw diff display
        st.code(diff_content, language="diff")
        return
    
    # Display each file's diff
    for file_diff in diff_sections:
        render_file_diff(file_diff)


def parse_diff(diff_content: str) -> List[dict]:
    """Parse diff content into structured data."""
    sections = []
    current_section = None
    lines = diff_content.split('\n')
    
    for line in lines:
        # File header
        if line.startswith('diff --git'):
            if current_section:
                sections.append(current_section)
            current_section = {
                'file': extract_filename_from_diff_line(line),
                'lines': [],
                'stats': {'additions': 0, 'deletions': 0}
            }
            current_section['lines'].append(('header', line))
        
        elif line.startswith('index') or line.startswith('---') or line.startswith('+++'):
            if current_section:
                current_section['lines'].append(('header', line))
        
        elif line.startswith('@@'):
            if current_section:
                current_section['lines'].append(('hunk', line))
        
        elif line.startswith('+') and not line.startswith('+++'):
            if current_section:
                current_section['lines'].append(('addition', line))
                current_section['stats']['additions'] += 1
        
        elif line.startswith('-') and not line.startswith('---'):
            if current_section:
                current_section['lines'].append(('deletion', line))
                current_section['stats']['deletions'] += 1
        
        else:
            if current_section and line.strip():
                current_section['lines'].append(('context', line))
    
    if current_section:
        sections.append(current_section)
    
    return sections


def extract_filename_from_diff_line(line: str) -> str:
    """Extract filename from diff header line."""
    # Extract from "diff --git a/file b/file"
    match = re.search(r'diff --git a/(.*?) b/', line)
    if match:
        return match.group(1)
    
    # Fallback to simple extraction
    parts = line.split()
    if len(parts) >= 4:
        return parts[3].lstrip('b/')
    
    return "unknown"


def render_file_diff(file_diff: dict):
    """Render diff for a single file."""
    filename = file_diff['file']
    stats = file_diff['stats']
    
    # File header with stats
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.write(f"📄 **{filename}**")
    
    with col2:
        if stats['additions'] > 0:
            st.write(f"🟢 +{stats['additions']}")
    
    with col3:
        if stats['deletions'] > 0:
            st.write(f"🔴 -{stats['deletions']}")
    
    # Render diff lines with colors
    with st.expander(f"View changes in {filename}", expanded=True):
        render_diff_lines(file_diff['lines'])
    
    st.divider()


def render_diff_lines(lines: List[Tuple[str, str]]):
    """Render individual diff lines with appropriate styling."""
    # Group lines for better rendering
    grouped_lines = group_diff_lines(lines)
    
    for line_type, content_lines in grouped_lines:
        if line_type == 'header':
            # Headers in gray
            st.code('\n'.join(content_lines), language=None)
        
        elif line_type == 'hunk':
            # Hunk headers in blue
            for line in content_lines:
                st.info(line)
        
        elif line_type == 'addition':
            # Additions in green background
            content = '\n'.join(content_lines)
            st.success(f"```\n{content}\n```")
        
        elif line_type == 'deletion':
            # Deletions in red background
            content = '\n'.join(content_lines)
            st.error(f"```\n{content}\n```")
        
        else:  # context
            # Context lines in normal style
            content = '\n'.join(content_lines)
            if content.strip():
                st.code(content, language=None)


def group_diff_lines(lines: List[Tuple[str, str]]) -> List[Tuple[str, List[str]]]:
    """Group consecutive lines of the same type."""
    if not lines:
        return []
    
    grouped = []
    current_type = None
    current_lines = []
    
    for line_type, line_content in lines:
        if line_type != current_type:
            if current_lines:
                grouped.append((current_type, current_lines))
            current_type = line_type
            current_lines = [line_content]
        else:
            current_lines.append(line_content)
    
    if current_lines:
        grouped.append((current_type, current_lines))
    
    return grouped


def render_compact_diff_summary(diff_content: str):
    """Render a compact summary of diff changes."""
    if not diff_content.strip():
        st.write("No changes")
        return
    
    # Count lines and files
    lines = diff_content.split('\n')
    files_changed = len([line for line in lines if line.startswith('diff --git')])
    additions = len([line for line in lines if line.startswith('+') and not line.startswith('+++')])
    deletions = len([line for line in lines if line.startswith('-') and not line.startswith('---')])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Files", files_changed)
    with col2:
        st.metric("Additions", additions, delta=f"+{additions}" if additions > 0 else None)
    with col3:
        st.metric("Deletions", deletions, delta=f"-{deletions}" if deletions > 0 else None)
    with col4:
        total_changes = additions + deletions
        st.metric("Total Changes", total_changes)


def render_side_by_side_diff(old_content: str, new_content: str, filename: str = ""):
    """Render a side-by-side diff view."""
    st.subheader(f"Side-by-Side View: {filename}" if filename else "Side-by-Side View")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Before**")
        st.code(old_content, language="python" if filename.endswith('.py') else None)
    
    with col2:
        st.write("**After**") 
        st.code(new_content, language="python" if filename.endswith('.py') else None)