"""
Nmap tool for DeepAgents (DeepAgents / LangChain compatible)

Behavior change: by default this tool now **forces XML output** (Nmap -oX) so the agent receives machine-readable XML output.
If you prefer structured python-nmap results instead, set `use_module=True` and `force_xml=False` explicitly.

This module provides a tool that can be passed into `create_deep_agent(...)` as a function.
It supports two execution modes:
  - Subprocess mode (default when forcing XML or when python-nmap not used): runs `nmap` with arguments and
    writes XML output to a temporary file (-oX). The XML content is returned in the response dict.
  - Module mode (optional): uses python-nmap `PortScanner` to get structured results when `use_module=True` and
    `force_xml=False`.

SECURITY: Only scan systems you are authorized to test.
"""

from __future__ import annotations

import shutil
import subprocess
import shlex
import os
import tempfile
from typing import Optional, Union, Dict, Any

# Try to import python-nmap (PortScanner)
try:
    import nmap as _pynmap  # python-nmap package
except Exception:
    _pynmap = None


class NmapToolError(RuntimeError):
    pass


def _find_nmap_executable() -> Optional[str]:
    return shutil.which("nmap")


def _run_subprocess_nmap(
    target: str,
    arguments: str = "",
    ports: Optional[str] = None,
    sudo: bool = False,
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    force_xml: bool = True,
) -> Dict[str, Any]:
    """Run nmap using subprocess and return dict with stdout/stderr/rc/command and xml content if requested.

    If force_xml=True, a temporary file is created and passed to nmap with -oX. The XML file is read and
    returned under the 'xml' key.
    """
    nmap_path = _find_nmap_executable()
    if not nmap_path:
        return {
            "success": False,
            "error": "nmap executable not found on PATH; install nmap",
        }

    cmd = []
    if sudo:
        cmd.append("sudo")
    cmd.append(nmap_path)

    # If ports provided, add -p before arguments/target
    if ports:
        cmd += ["-p", ports]

    # Prepare temporary xml file if requested
    xml_path = None
    if force_xml:
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
        xml_path = tf.name
        tf.close()  # will be written by nmap
        cmd += ["-oX", xml_path]

    # Safe split of arguments (respect quoting)
    if arguments:
        cmd += shlex.split(arguments)

    # Append target(s) last
    cmd.append(target)

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
        # cleanup temp file if we created one
        if xml_path and os.path.exists(xml_path):
            try:
                os.unlink(xml_path)
            except Exception:
                pass
        return {
            "success": False,
            "error": f"timeout after {timeout}s: {e}",
            "command": cmd,
        }
    except Exception as e:
        if xml_path and os.path.exists(xml_path):
            try:
                os.unlink(xml_path)
            except Exception:
                pass
        return {
            "success": False,
            "error": f"failed to execute nmap: {e}",
            "command": cmd,
        }

    result = {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": cmd,
    }

    if xml_path and os.path.exists(xml_path):
        try:
            with open(xml_path, "r", encoding="utf-8", errors="replace") as f:
                xml_content = f.read()
            result["xml"] = xml_content
        except Exception as e:
            result["xml_error"] = str(e)
        finally:
            try:
                os.unlink(xml_path)
            except Exception:
                pass

    return result


def _run_module_nmap(
    target: str, ports: Optional[str] = None, arguments: Optional[str] = None
) -> Dict[str, Any]:
    """Run nmap using python-nmap's PortScanner and return the raw scan dict.

    Note: python-nmap still shells out to the nmap binary under the hood, so nmap must be installed.
    """
    if _pynmap is None:
        return {
            "success": False,
            "error": "python-nmap package not installed (pip install python-nmap)",
        }

    scanner = _pynmap.PortScanner()
    try:
        # PortScanner.scan(hosts, ports=None, arguments='')
        scan_kwargs = {}
        if ports:
            scan_kwargs["ports"] = ports
        if arguments:
            scan_kwargs["arguments"] = arguments

        result = scanner.scan(hosts=target, **scan_kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def nmap_tool(
    target: str,
    *,
    arguments: str = "",
    ports: Optional[str] = None,
    use_module: bool = True,
    force_subprocess: bool = False,
    sudo: bool = False,
    timeout: Optional[int] = 300,
    force_xml: bool = True,
    return_raw: bool = False,
) -> Dict[str, Any]:
    """
    DeepAgents-compatible nmap tool function.

    Default behavior: `force_xml=True` meaning the tool will run nmap via subprocess and return
    XML output (-oX) inside the returned dict under the key 'xml'. If you want python-nmap's
    structured PortScanner.scan() result instead, call with `use_module=True` and `force_xml=False`.

    Parameters
    ----------
    target: str
        Host, IP, CIDR, or list of hosts string to scan.
    arguments: str
        Extra nmap arguments string (e.g. '-sV -O --script vuln'). Will be safely split
        when using subprocess mode. When using python-nmap, this string will be passed
        as the `arguments` param.
    ports: Optional[str]
        Port list/range passed as `-p` to nmap (e.g. '1-65535' or '22,80,443').
    use_module: bool
        Prefer using python-nmap if installed. Note: if force_xml=True then subprocess
        execution will be used to ensure XML output.
    force_subprocess: bool
        If True, force subprocess invocation even if python-nmap exists.
    sudo: bool
        Prepend 'sudo' to subprocess invocation (agent environment must allow sudo).
    timeout: Optional[int]
        Subprocess timeout in seconds. Ignored for python-nmap mode.
    force_xml: bool
        If True (default) run nmap with -oX to produce XML output and return it.
    return_raw: bool
        If True and using module mode, return raw PortScanner.scan() dict.

    Returns
    -------
    Dict[str, Any]
        A dictionary with keys like 'success', 'stdout', 'stderr', 'returncode', 'command', 'xml' or
        'result' for python-nmap outputs.
    """

    print("DEBUG: nmap_tool called with", {"target": target, "arguments": arguments, "ports": ports})


    if not target:
        return {"success": False, "error": "target is required"}

    # If force_subprocess is requested, use subprocess path
    if force_subprocess:
        return _run_subprocess_nmap(
            target=target,
            arguments=arguments,
            ports=ports,
            sudo=sudo,
            timeout=timeout,
            force_xml=force_xml,
        )

    # If force_xml is requested, prefer subprocess to guarantee XML output
    if force_xml:
        return _run_subprocess_nmap(
            target=target,
            arguments=arguments,
            ports=ports,
            sudo=sudo,
            timeout=timeout,
            force_xml=True,
        )

    # At this point force_xml is False. If user requested module and it's available, use it
    if use_module and _pynmap is not None:
        module_result = _run_module_nmap(
            target=target, ports=ports, arguments=arguments
        )
        if return_raw:
            return module_result.get("result", module_result)
        return module_result

    # Fallback to subprocess
    return _run_subprocess_nmap(
        target=target,
        arguments=arguments,
        ports=ports,
        sudo=sudo,
        timeout=timeout,
        force_xml=False,
    )


# Optional helper to create a LangChain-style @tool wrapper (if you use langchain tool decorator):
def make_langchain_tool():
    try:
        # Lazy import to avoid hard dependency
        from langchain.tools import tool as _lc_tool

        @_lc_tool
        def _wrapped(
            target: str, arguments: str = "", ports: Optional[str] = None, **kwargs
        ):
            return nmap_tool(target=target, arguments=arguments, ports=ports, **kwargs)

        return _wrapped
    except Exception:
        # langchain not installed or import failed
        return nmap_tool


if __name__ == "__main__":
    print("Nmap deepagents tool demo — default: force XML output")
    res = nmap_tool("127.0.0.1", arguments="-sV -T4", ports="1-1024")
    print(res)
