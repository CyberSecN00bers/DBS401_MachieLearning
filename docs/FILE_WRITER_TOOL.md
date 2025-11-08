# Real Filesystem Writer Tool Documentation

## Overview

The `file_writer.py` tool provides real filesystem write capabilities for the reporting subagent, addressing the limitation of deepagents' `write_file` which only operates on a virtual filesystem.

## Problem Statement

**Issue**: The deepagents `write_file` function writes to a virtual/in-memory filesystem that doesn't persist files to disk. This is problematic for penetration testing reports that need to be:
- Saved for client delivery
- Archived for compliance
- Reviewed after agent execution completes

**Solution**: Custom `write_report_file()` tool that writes directly to the real filesystem with security safeguards.

---

## Features

### ✅ Core Capabilities

1. **Real Filesystem Persistence**: Files are written to actual disk, not virtual memory
2. **Multiple Format Support**: TXT, JSON, HTML, MD (Markdown)
3. **Security Hardening**: 
   - Filename sanitization (prevents directory traversal)
   - Path validation (ensures writes stay in allowed directory)
   - Safe character filtering
4. **Automatic Timestamping**: Optional timestamp suffix for unique filenames
5. **Append Mode**: Can append to existing files or overwrite
6. **JSON Pretty-Printing**: Automatically formats JSON with proper indentation
7. **HTML Template Generator**: Pre-built professional report template

---

## Usage Examples

### Basic Text Report

```python
from tools.file_writer import file_writer_tool

result = file_writer_tool(
    content="# Penetration Test Report\n\nTarget: 192.168.1.100\n\nFindings:\n- SQL Injection on /login",
    filename="pentest_report",
    file_format="txt"
)

print(result["file_path"])  # reports/pentest_report_20250107_143022.txt
```

### JSON Findings Export

```python
import json

findings = {
    "target": "192.168.1.100",
    "scan_date": "2025-01-07",
    "findings": [
        {
            "id": "FIND-001",
            "severity": "CRITICAL",
            "title": "SQL Injection in Login Form",
            "description": "The login endpoint is vulnerable to SQL injection...",
            "cvss": 9.8,
            "remediation": "Use parameterized queries"
        }
    ]
}

result = file_writer_tool(
    content=json.dumps(findings),
    filename="findings",
    file_format="json"
)
# Automatically pretty-prints JSON with 2-space indentation
```

### HTML Report with Template

```python
from tools.file_writer import file_writer_tool, create_html_report_template

# Create template
template = create_html_report_template(title="Security Assessment Report")

# Fill in content
html_content = template.replace("{{EXECUTIVE_SUMMARY}}", 
    "This assessment identified 3 critical vulnerabilities...")
html_content = html_content.replace("{{TARGET_INFO}}", 
    "<strong>Target:</strong> 192.168.1.100<br><strong>Date:</strong> 2025-01-07")
html_content = html_content.replace("{{FINDINGS}}", 
    "<div class='finding severity-critical'><h3>SQL Injection</h3><p>Details...</p></div>")

# Write to file
result = file_writer_tool(
    content=html_content,
    filename="security_report",
    file_format="html"
)
```

### Markdown Documentation

```python
markdown_content = """
# Penetration Test Report

## Executive Summary
During this assessment, we identified **3 critical** and **5 high-severity** vulnerabilities.

## Findings

### 1. SQL Injection (CRITICAL)
- **Location**: `/api/login`
- **Impact**: Database compromise, data exfiltration
- **Remediation**: Implement parameterized queries

### 2. Weak Credentials (HIGH)
- **Location**: Administrator accounts
- **Impact**: Unauthorized access
- **Remediation**: Enforce strong password policy
"""

result = file_writer_tool(
    content=markdown_content,
    filename="pentest_report",
    file_format="md"
)
```

### Append Mode (Log-Style)

```python
# First write
file_writer_tool(
    content="[2025-01-07 14:30] Scan started\n",
    filename="scan_log",
    file_format="txt",
    create_timestamp=False  # Don't timestamp so we can append later
)

# Append more logs
file_writer_tool(
    content="[2025-01-07 14:35] Found 12 open ports\n",
    filename="scan_log",
    file_format="txt",
    append=True,
    create_timestamp=False
)
```

---

## Function Reference

### `write_report_file()`

Main tool function for writing files to the real filesystem.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | str | *required* | Content to write to file |
| `filename` | str | *required* | Filename without extension |
| `output_dir` | str | `"reports"` | Directory for output files |
| `file_format` | Literal | `"txt"` | File extension: txt, json, html, md |
| `append` | bool | `False` | If True, append; if False, overwrite |
| `create_timestamp` | bool | `True` | Add timestamp suffix to filename |

**Returns:**

```python
{
    "status": "success",
    "file_path": "reports/pentest_report_20250107_143022.txt",
    "absolute_path": "D:\\Uni\\...\\reports\\pentest_report_20250107_143022.txt",
    "size_bytes": 2048,
    "size_kb": 2.0,
    "mode": "created",  # or "appended"
    "message": "Successfully created reports/pentest_report_20250107_143022.txt"
}
```

**Raises:**
- `FileWriterError`: Path validation failure, write permission error, etc.

---

### `create_html_report_template()`

Generates professional HTML template for penetration test reports.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | `"Penetration Test Report"` | HTML page title |
| `css_style` | Optional[str] | None | Custom CSS (uses default if None) |

**Returns:**
- HTML string with placeholders: `{{EXECUTIVE_SUMMARY}}`, `{{TARGET_INFO}}`, `{{FINDINGS}}`, `{{RECOMMENDATIONS}}`, `{{TECHNICAL_DETAILS}}`

**Template Features:**
- Responsive design (max-width 1200px)
- Gradient header (purple theme)
- Card-based sections with shadows
- Severity color coding (Critical=red, High=orange, Medium=yellow, Low=blue)
- Styled code blocks
- Professional table formatting

---

## Security Features

### Filename Sanitization

Dangerous characters are automatically removed/replaced:

```python
# Before sanitization
filename = "../../../etc/passwd"

# After sanitization
sanitized = "___etc_passwd"  # Path separators replaced with underscores
```

**Blocked Characters:**
- `/`, `\` (path separators)
- `..` (directory traversal)
- `\0` (null byte)
- `<`, `>`, `:`, `"`, `|`, `?`, `*` (filesystem dangerous chars)

### Path Validation

All file paths are validated to ensure they stay within the allowed directory:

```python
# ✅ ALLOWED
output_dir = Path("reports")
file_path = Path("reports/pentest_report.txt")
# file_path is within output_dir

# ❌ BLOCKED - Raises FileWriterError
output_dir = Path("reports")
file_path = Path("/etc/passwd")  # Outside allowed directory
```

### Directory Creation

Output directories are created automatically with `mkdir(parents=True, exist_ok=True)`:

```python
# If "reports" doesn't exist, it will be created
file_writer_tool(content="test", filename="report", output_dir="reports/2025/january")
# Creates: reports/2025/january/
```

---

## Integration with Reporting Subagent

The tool is automatically available to the reporting subagent:

```python
# agent/subagent/reporting_subagent.py
from tools.file_writer import file_writer_tool, create_html_report_template

DEFAULT_TOOLS = [ls, read_file, edit_file, file_writer_tool]
```

**Agent Prompt Usage:**

The reporting agent can now be instructed to:

```markdown
You are a security reporting specialist. When generating reports:

1. Use `file_writer_tool` to save findings to disk
2. Generate both JSON (machine-readable) and HTML (human-readable) reports
3. Use `create_html_report_template()` for professional formatting
4. Organize findings by severity (CRITICAL > HIGH > MEDIUM > LOW)
5. Include remediation steps for each finding

Example report structure:
- findings_20250107.json (raw data)
- pentest_report_20250107.html (formatted report for client)
- executive_summary_20250107.md (high-level overview)
```

---

## File Organization

### Default Directory Structure

```
reports/
├── pentest_report_20250107_143022.html
├── findings_20250107_143022.json
├── executive_summary_20250107_143022.md
├── scan_logs_20250107_143022.txt
└── remediation_guide_20250107_143022.md
```

### Custom Directory Structure

```python
# Organize by target
file_writer_tool(
    content=findings,
    filename="report",
    output_dir="reports/192.168.1.100"
)

# Organize by date
file_writer_tool(
    content=findings,
    filename="report",
    output_dir="reports/2025/01/07"
)

# Organize by client
file_writer_tool(
    content=findings,
    filename="report",
    output_dir="reports/clients/acme_corp"
)
```

---

## Testing

The tool includes built-in tests in `__main__`:

```bash
python tools/file_writer.py
```

**Expected Output:**

```
Testing real filesystem writer tool...
✅ Test 1: Successfully created reports/test_report_20250107_143022.txt
   Path: reports/test_report_20250107_143022.txt
✅ Test 2: Successfully created reports/test_findings_20250107_143022.json
   Size: 0.15 KB
✅ Test 3: Successfully created reports/test_html_report_20250107_143022.html
   Absolute path: D:\Uni\...\reports\test_html_report_20250107_143022.html
```

---

## Comparison: Virtual vs Real Filesystem

| Feature | deepagents `write_file` | `file_writer_tool` |
|---------|-------------------------|-------------------|
| Filesystem | Virtual (in-memory) | Real (disk) |
| Persistence | ❌ Lost after execution | ✅ Persists permanently |
| File Access | Only via agent tools | ✅ Standard OS file access |
| Security | Sandboxed | ✅ Path validation + sanitization |
| Format Support | Text only | TXT, JSON, HTML, MD |
| JSON Formatting | Manual | ✅ Automatic pretty-print |
| Templates | None | ✅ HTML report template |
| Timestamping | Manual | ✅ Automatic option |

---

## Best Practices

### 1. Use Descriptive Filenames

```python
# ❌ BAD
file_writer_tool(content=data, filename="report")

# ✅ GOOD
file_writer_tool(content=data, filename="sql_injection_findings_acme_corp")
```

### 2. Organize by Purpose

```python
# Client deliverables
file_writer_tool(content=html_report, filename="client_report", output_dir="reports/deliverables")

# Internal documentation
file_writer_tool(content=raw_data, filename="raw_findings", output_dir="reports/internal")

# Compliance archives
file_writer_tool(content=audit_log, filename="audit_log", output_dir="reports/archives/2025")
```

### 3. Generate Multiple Formats

```python
findings_data = {...}

# Machine-readable for automation
file_writer_tool(
    content=json.dumps(findings_data),
    filename="findings",
    file_format="json"
)

# Human-readable for analysts
html = create_html_report_template()
# ... fill template ...
file_writer_tool(
    content=html,
    filename="findings_report",
    file_format="html"
)

# Executive summary
markdown = generate_executive_summary(findings_data)
file_writer_tool(
    content=markdown,
    filename="executive_summary",
    file_format="md"
)
```

### 4. Handle Large Reports

```python
# For very large reports, disable timestamps to enable chunking/appending
file_writer_tool(
    content="# Part 1: Reconnaissance\n...",
    filename="full_report",
    file_format="md",
    create_timestamp=False
)

file_writer_tool(
    content="\n# Part 2: Vulnerability Scanning\n...",
    filename="full_report",
    file_format="md",
    append=True,
    create_timestamp=False
)
```

---

## Troubleshooting

### Issue: FileWriterError - Permission Denied

**Cause**: No write permission to output directory

**Solution**:
```bash
# Windows
icacls reports /grant Users:F

# Linux/Mac
chmod 755 reports
```

### Issue: Files Not Found After Creation

**Cause**: Working directory confusion

**Solution**:
```python
# Use absolute_path from return value
result = file_writer_tool(content="test", filename="report")
print(f"File saved at: {result['absolute_path']}")
```

### Issue: Filename Contains Weird Underscores

**Cause**: Sanitization replaced special characters

**Solution**: Use only alphanumeric characters, hyphens, underscores in filenames:
```python
# ❌ BAD - will be sanitized
filename = "report:target/192.168.1.100"  # becomes "report_target_192.168.1.100"

# ✅ GOOD
filename = "report_target_192_168_1_100"
```

---

## Future Enhancements

Potential improvements for future versions:

1. **PDF Generation**: Add PDF export using ReportLab
2. **Compression**: Auto-compress large reports with gzip
3. **Encryption**: Option to encrypt sensitive reports (AES-256)
4. **Cloud Upload**: Direct upload to S3/Azure Blob Storage
5. **Email Integration**: Auto-send reports via SMTP
6. **Version Control**: Auto-commit reports to git
7. **Digital Signatures**: Sign reports with GPG/PGP

---

## License

This tool is part of the DBS401 Machine Learning Penetration Testing Framework.
See LICENSE file for details.
