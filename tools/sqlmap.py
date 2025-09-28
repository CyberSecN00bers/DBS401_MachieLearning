"""
SQLMap tool for DeepAgents (DeepAgents / LangChain compatible)

This module provides a DeepAgents-compatible tool function `sqlmap_tool(...)` that lets an agent
run sqlmap with essentially full control of the command-line options. The tool enforces a safe
subprocess invocation (no shell=True), and by default appends `--batch` so sqlmap runs non-interactively.

Usage notes / security
- Only run sqlmap against targets you are authorized to test.
- sqlmap must be installed and available on PATH (executable named `sqlmap` or `sqlmap.py`).

Features
- Automatically finds sqlmap binary on PATH.
- Accepts `arguments` string (e.g. "-p id --risk=3 --level=5 --threads=10") which will be safely split.
- Convenience parameters: `url` (will add -u url if not provided), `data`, `cookie`, `headers` (headers dict will be converted to repeated --headers "Name: Value").
- Default `--batch` is appended if user doesn't include it in `arguments`.
- Optional `auto_add_url` (default True) will add -u <url> when a url argument is provided.
- Returns a dict with success, stdout, stderr, returncode, and the executed command.

Example in DeepAgents tool list:
    agent = create_deep_agent([sqlmap_tool], "scan the given url and return vulnerabilities")

"""

from __future__ import annotations

import shutil
import subprocess
import shlex
import os
from typing import Optional, Dict, Any, List


class SQLMapToolError(RuntimeError):
    pass


def _find_sqlmap_executable() -> Optional[str]:
    # Common names: `sqlmap` or `sqlmap.py`
    candidates = ["sqlmap", "sqlmap.py"]
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return None


def _dict_to_header_args(headers: Dict[str, str]) -> List[str]:
    args: List[str] = []
    for k, v in headers.items():
        # sqlmap can accept -H/--headers as a single header string; to be safe provide repeated --headers
        # However many installations accept a single --headers string with multiple headers separated by '\r\n'
        args += ["--headers", f"{k}: {v}"]
    return args


def sqlmap_tool(
    url: Optional[str] = None,
    *,
    arguments: str = "",
    data: Optional[str] = None,
    cookie: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = 600,
    sudo: bool = False,
    auto_add_url: bool = True,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    DeepAgents-compatible wrapper to run sqlmap.

    Parameters
    ----------
    url: Optional[str]
        Target URL. If provided and `arguments` doesn't already include -u/--url and auto_add_url=True,
        the tool will add `-u <url>` automatically.
    arguments: str
        Extra sqlmap arguments string provided by the agent (e.g. "-p id --risk=3 --level=5").
    data: Optional[str]
        Request body to pass via --data if the target expects POST.
    cookie: Optional[str]
        Cookie header string to pass via --cookie.
    headers: Optional[Dict[str,str]]
        Extra headers to pass; will be converted to --headers entries.
    timeout: Optional[int]
        Subprocess timeout in seconds.
    sudo: bool
        Prepend 'sudo' to invocation.
    auto_add_url: bool
        If True and url provided and -u/--url not present in arguments, automatically add it.
    env: Optional[Dict[str,str]]
        Environment variables for subprocess; defaults to os.environ.

    Returns
    -------
    Dict[str, Any]
        A dict containing at least: success (bool), stdout (str), stderr (str), returncode (int), command (list).
    """
    sqlmap_path = _find_sqlmap_executable()
    if not sqlmap_path:
        return {
            "success": False,
            "error": "sqlmap executable not found on PATH; install sqlmap",
        }

    # Build command safely as a list
    cmd: List[str] = []
    if sudo:
        cmd.append("sudo")
    cmd.append(sqlmap_path)

    # If agent provided arguments, split safely
    arg_list: List[str] = shlex.split(arguments) if arguments else []

    # Ensure --batch is present by default (non-interactive)
    if not any(a == "--batch" for a in arg_list):
        arg_list.insert(0, "--batch")

    # Add data, cookie, headers if provided and not already present in arg_list
    if data and not any(a in ("--data", "-d") for a in arg_list):
        arg_list += ["--data", data]

    if cookie and not any(a == "--cookie" for a in arg_list):
        arg_list += ["--cookie", cookie]

    if headers:
        header_args = _dict_to_header_args(headers)
        # only add if --headers not already provided
        if not any(a == "--headers" for a in arg_list):
            arg_list += header_args

    # If url supplied and not present in arg_list, add -u <url>
    if url and auto_add_url and not any(a in ("-u", "--url") for a in arg_list):
        arg_list += ["-u", url]

    # Combine
    cmd += arg_list

    # Run subprocess safely
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env or os.environ.copy(),
        )
    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "error": f"timeout after {timeout}s: {e}",
            "command": cmd,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"failed to execute sqlmap: {e}",
            "command": cmd,
        }

    result = {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": cmd,
    }

    return result


# Optional compatibility wrapper for LangChain @tool decorator
def make_langchain_tool():
    try:
        from langchain.tools import tool as _lc_tool

        @_lc_tool
        def _wrapped(url: Optional[str] = None, arguments: str = "", **kwargs):
            return sqlmap_tool(url=url, arguments=arguments, **kwargs)

        return _wrapped
    except Exception:
        return sqlmap_tool


if __name__ == "__main__":
    print("sqlmap tool demo — default: --batch added")
    # Example: run sqlmap non-interactively against example.com
    res = sqlmap_tool(
        url="http://example.com/vuln.php?id=1", arguments="-p id --risk=2 --level=2"
    )
    print(res)
