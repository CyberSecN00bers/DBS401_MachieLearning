# Developer Quick Start Guide

## 🚀 Getting Started

### Installation
```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

### Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# GOOGLE_API_KEY=your_key_here
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_validator_service.py

# Run only unit tests
pytest -m unit

# Run with verbose output
pytest -v

# View coverage report
# Open htmlcov/index.html in browser
```

---

## 🔍 Code Quality Tools

### Formatting with Black
```bash
# Format all Python files
black .

# Check what would be formatted (dry-run)
black --check .

# Format specific file
black services/io_service.py
```

### Linting with Ruff
```bash
# Lint all files
ruff check .

# Auto-fix issues
ruff check --fix .

# Check specific file
ruff check main.py
```

### Type Checking with MyPy
```bash
# Type check all files
mypy .

# Check specific module
mypy services/

# Generate HTML report
mypy --html-report mypy-report .
```

---

## 📝 Logging

### Application Logs
- **File:** `pentest.log`
- **Format:** Timestamp, Logger Name, Level, Message
- **Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting operation")
logger.warning("Potential issue detected")
logger.error("Operation failed", exc_info=True)
```

### Audit Logs
- **Directory:** `logs/`
- **Format:** JSONL (one JSON object per line)
- **File Pattern:** `audit_YYYYMMDD_HHMMSS.jsonl`

```python
from services.audit_service import get_audit_logger

audit = get_audit_logger()
audit.log_tool_invocation(
    tool_name="nmap",
    arguments={"target": "192.168.1.1"},
    target="192.168.1.1",
    approved_by="admin"
)
```

---

## 🏗️ Project Structure

```
DBS401_MachieLearning/
├── agent/                  # AI agent orchestration
│   ├── orchestrator.py    # Main orchestration logic
│   ├── pentest.py         # Pentesting agent
│   ├── prompt/            # AI prompts
│   └── subagent/          # Specialized subagents
├── configs/               # Configuration
│   └── app_configs.py     # App configuration
├── services/              # Service layer
│   ├── audit_service.py   # Audit logging (NEW)
│   ├── human_in_the_loop_service.py
│   ├── io_service.py      # I/O utilities
│   └── validator_service.py
├── tools/                 # Security tools
│   ├── nmap.py           # Nmap wrapper
│   ├── sqlmap.py         # SQLMap wrapper
│   ├── mssql.py          # MSSQL client
│   └── authenticate.py    # Auth tools
├── utils/                # Utilities
│   ├── system_check.py   # System checks
│   └── installer.py      # Dependency installer
├── tests/                # Test suite (NEW)
│   ├── conftest.py       # Pytest fixtures
│   ├── test_io_service.py
│   └── test_validator_service.py
├── logs/                 # Log files (generated)
├── main.py               # Entry point
├── pyproject.toml        # Project config
├── pytest.ini            # Pytest config (NEW)
└── .env                  # Environment variables
```

---

## 🔐 Security Best Practices

### 1. Authorization
Always verify authorization before testing:
```python
io = safe_input("Do you confirm authorization? [yes/No]:")
if io.strip().lower() not in ("y", "yes"):
    notify("Authorization not confirmed. Exiting.")
    exit(1)
```

### 2. Audit Everything
Log all security-sensitive operations:
```python
audit.log_tool_invocation(tool_name, args, target, user)
audit.log_database_query(query, database, target)
audit.log_human_decision(decision, context, user)
```

### 3. Human-in-the-Loop
All destructive operations require human approval via HITL service.

### 4. Credentials
- Never commit credentials
- Use environment variables
- Encrypt sensitive data at rest

---

## 🐛 Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### View Agent Stream
Uncomment in orchestrator.py:
```python
for chunk in agent.stream(next_input, config=config):
    print("STREAM->", chunk)  # Add this line
    last_chunk = dict(chunk)
```

### Check Audit Logs
```bash
# View latest audit log
cat logs/audit_*.jsonl | jq .

# Count events by type
cat logs/audit_*.jsonl | jq -r .event_type | sort | uniq -c
```

---

## 📦 Adding New Tools

### 1. Create Tool File
```python
# tools/my_tool.py
def my_tool(target: str, arguments: str) -> dict:
    """Tool description"""
    # Implementation
    return {"success": True, "result": "..."}
```

### 2. Add to Agent
```python
# agent/orchestrator.py
from tools.my_tool import my_tool

all_tools = [nmap_tool, sqlmap_tool, my_tool]  # Add here
```

### 3. Add to Subagent
```python
# agent/subagent/my_subagent.py
from tools.my_tool import my_tool

DEFAULT_TOOLS = [my_tool, ...]
```

### 4. Write Tests
```python
# tests/test_my_tool.py
def test_my_tool():
    result = my_tool("192.168.1.1", "-v")
    assert result["success"] is True
```

---

## 🎯 Common Tasks

### Run the Application
```bash
uv run main.py
```

### Run Tests Before Commit
```bash
pytest && black --check . && ruff check .
```

### Generate Coverage Report
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html  # or start htmlcov/index.html on Windows
```

### Update Dependencies
```bash
uv sync
```

### Add New Dependency
```bash
# Edit pyproject.toml, then:
uv sync
```

---

## 📚 Additional Resources

- **DeepAgents Docs:** https://docs.deepagents.ai/
- **LangChain Docs:** https://python.langchain.com/
- **Pytest Docs:** https://docs.pytest.org/
- **Ruff Docs:** https://docs.astral.sh/ruff/

---

## ⚠️ Troubleshooting

### Import Error: deepagents
```bash
uv sync
# or
pip install deepagents
```

### Type Check Errors
```bash
# Add type: ignore comment
result = some_function()  # type: ignore

# Or add to pyproject.toml
[tool.mypy]
ignore_missing_imports = true
```

### Test Failures
```bash
# Run with verbose output
pytest -v -s

# Run specific test
pytest tests/test_validator_service.py::TestIPValidation::test_valid_ipv4
```

---

**Need Help?** Check the logs in `pentest.log` and `logs/audit_*.jsonl`
