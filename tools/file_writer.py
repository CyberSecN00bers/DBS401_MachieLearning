"""
Real filesystem writer tool for DeepAgents reporting

This tool writes content to actual files on the filesystem, unlike deepagents' 
write_file which operates on a virtual filesystem. Designed for generating 
penetration test reports that persist after the agent execution completes.

SECURITY: 
- Only writes to authorized directories
- Validates paths to prevent directory traversal
- Supports multiple output formats (TXT, JSON, HTML, MD)
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from datetime import datetime


class FileWriterError(RuntimeError):
    """Custom exception for file writer errors"""
    pass


def write_report_file(
    content: str,
    filename: str,
    output_dir: str = "reports",
    file_format: Literal["txt", "json", "html", "md"] = "txt",
    append: bool = False,
    create_timestamp: bool = True,
) -> Dict[str, Any]:
    """
    Write content to a real file on the filesystem.
    
    This tool creates actual files that persist after agent execution, making it
    suitable for generating penetration test reports, findings documentation, and
    remediation guides.
    
    Args:
        content: The content to write to the file
        filename: Name of the file (without extension, added automatically)
        output_dir: Directory to write the file (default: "reports")
        file_format: File format/extension (txt, json, html, md)
        append: If True, append to existing file; if False, overwrite
        create_timestamp: If True, add timestamp to filename
        
    Returns:
        Dict with status, file_path, size_bytes, and message
        
    Raises:
        FileWriterError: If path validation fails or write operation fails
        
    Example:
        >>> result = write_report_file(
        ...     content="# Penetration Test Report\\n\\nFindings...",
        ...     filename="pentest_report",
        ...     file_format="md"
        ... )
        >>> print(result["file_path"])
        reports/pentest_report_20250107_143022.md
    """
    try:
        # Validate and sanitize filename
        filename = _sanitize_filename(filename)
        
        # Add timestamp if requested
        if create_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}"
        
        # Add extension
        filename = f"{filename}.{file_format}"
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Construct full file path
        file_path = output_path / filename
        
        # Validate path to prevent directory traversal
        _validate_path(file_path, output_path)
        
        # Special handling for JSON format
        if file_format == "json":
            content = _format_json_content(content)
        
        # Write the file
        mode = "a" if append else "w"
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)
            if append:
                f.write("\n")  # Add newline when appending
        
        # Get file size
        size_bytes = file_path.stat().st_size
        
        return {
            "status": "success",
            "file_path": str(file_path),
            "absolute_path": str(file_path.absolute()),
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 2),
            "mode": "appended" if append else "created",
            "message": f"Successfully {'appended to' if append else 'created'} {file_path}",
        }
        
    except FileWriterError:
        raise
    except Exception as e:
        raise FileWriterError(f"Failed to write file: {str(e)}") from e


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.
    
    Removes or replaces dangerous characters and prevents directory traversal.
    """
    # Remove path separators and dangerous characters
    dangerous_chars = ['/', '\\', '..', '\0', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "report"
    
    return sanitized


def _validate_path(file_path: Path, output_dir: Path) -> None:
    """
    Validate that the file path is within the allowed output directory.
    
    Prevents directory traversal attacks.
    """
    try:
        # Resolve to absolute paths
        file_abs = file_path.resolve()
        dir_abs = output_dir.resolve()
        
        # Check if file is within output directory
        if not str(file_abs).startswith(str(dir_abs)):
            raise FileWriterError(
                f"Security: File path {file_abs} is outside allowed directory {dir_abs}"
            )
    except Exception as e:
        raise FileWriterError(f"Path validation failed: {str(e)}") from e


def _format_json_content(content: str) -> str:
    """
    Format content as pretty-printed JSON if it's valid JSON.
    
    If content is already JSON string, parse and reformat.
    If content is plain text, return as-is.
    """
    try:
        # Try to parse as JSON
        data = json.loads(content)
        # Pretty print with 2-space indent
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # Not JSON, return as-is
        return content


def create_html_report_template(
    title: str = "Penetration Test Report",
    css_style: Optional[str] = None,
) -> str:
    """
    Create a basic HTML template for penetration test reports.
    
    Args:
        title: HTML page title
        css_style: Optional custom CSS (if None, uses default styling)
        
    Returns:
        HTML template string with placeholders for content
    """
    if css_style is None:
        css_style = """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .section {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .finding {
            border-left: 4px solid #e74c3c;
            padding-left: 15px;
            margin: 15px 0;
        }
        .severity-critical { border-left-color: #c0392b; background-color: #fadbd8; }
        .severity-high { border-left-color: #e74c3c; background-color: #f9ebea; }
        .severity-medium { border-left-color: #f39c12; background-color: #fef5e7; }
        .severity-low { border-left-color: #3498db; background-color: #ebf5fb; }
        .code-block {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
        }
        """
    
    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css_style}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <p>{{EXECUTIVE_SUMMARY}}</p>
    </div>
    
    <div class="section">
        <h2>Target Information</h2>
        <p>{{TARGET_INFO}}</p>
    </div>
    
    <div class="section">
        <h2>Findings</h2>
        {{FINDINGS}}
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        {{RECOMMENDATIONS}}
    </div>
    
    <div class="section">
        <h2>Technical Details</h2>
        {{TECHNICAL_DETAILS}}
    </div>
</body>
</html>
"""
    return template


# Export the main tool for use with DeepAgents
file_writer_tool = write_report_file


if __name__ == "__main__":
    # Example usage
    print("Testing real filesystem writer tool...")
    
    # Test 1: Write a simple text report
    result = write_report_file(
        content="# Penetration Test Report\n\nThis is a test report.",
        filename="test_report",
        file_format="txt",
    )
    print(f"✅ Test 1: {result['message']}")
    print(f"   Path: {result['file_path']}")
    
    # Test 2: Write JSON data
    json_data = json.dumps({
        "target": "192.168.1.100",
        "findings": [
            {"severity": "high", "title": "SQL Injection"},
            {"severity": "medium", "title": "Weak Credentials"}
        ]
    })
    result = write_report_file(
        content=json_data,
        filename="test_findings",
        file_format="json",
    )
    print(f"✅ Test 2: {result['message']}")
    print(f"   Size: {result['size_kb']} KB")
    
    # Test 3: Create HTML report
    html_content = create_html_report_template()
    html_content = html_content.replace("{{EXECUTIVE_SUMMARY}}", "Test summary")
    html_content = html_content.replace("{{TARGET_INFO}}", "192.168.1.100")
    html_content = html_content.replace("{{FINDINGS}}", "<p>Test findings</p>")
    html_content = html_content.replace("{{RECOMMENDATIONS}}", "<p>Test recommendations</p>")
    html_content = html_content.replace("{{TECHNICAL_DETAILS}}", "<p>Test details</p>")
    
    result = write_report_file(
        content=html_content,
        filename="test_html_report",
        file_format="html",
    )
    print(f"✅ Test 3: {result['message']}")
    print(f"   Absolute path: {result['absolute_path']}")
