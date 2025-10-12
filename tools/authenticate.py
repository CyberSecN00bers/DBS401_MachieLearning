"""
Safer MS SQL credential-check tool for DeepAgents / LangChain

This file implements a LangChain/DeepAgents-compatible tool that **verifies a single
username/password pair** against a Microsoft SQL Server instance. It is intentionally
limited to a single credential check to avoid providing brute-force capability.

DO NOT USE THIS TOOL TO ATTEMPT UNAUTHORIZED ACCESS — use only on systems you own
or have explicit permission to test.

Dependencies (one of the below):
  - pytds    (preferred, pure-Python TDS driver)
  - pyodbc   (ODBC)
  - pymssql  (fallback older driver)

Example usage:
  res = mssql_check_credentials(host='10.0.0.5', port=1433, username='sa', password='P@ssw0rd')

Return value: dict with keys: success (bool), error (str, optional), details (dict, optional)

This is safe for integrating into an agent because it requires the agent to provide a
specific username/password pair; it will NOT iterate over lists, threads or do "brute force".
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import socket
import traceback

# Preferred: pytds, fallback: pyodbc, then pymssql
try:
    import pytds  # type: ignore
except Exception:
    pytds = None

try:
    import pyodbc  # type: ignore
except Exception:
    pyodbc = None

try:
    import pymssql  # type: ignore
except Exception:
    pymssql = None


def _check_port_open(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _try_pytds_connect(
    host: str,
    port: int,
    username: str,
    password: str,
    database: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    """Attempt connection using pytds.connect"""
    if not pytds:
        return {"ok": False, "error": "pytds not installed"}
    try:
        # pytds.connect accepts host, port, user, password, database, autocommit, etc.
        conn = pytds.connect(
            server=host,
            port=port,
            user=username,
            password=password,
            database=database or None,
            autocommit=True,
            timeout=int(timeout),
        )
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
            cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return {"ok": True, "method": "pytds"}
    except Exception as e:
        return {
            "ok": False,
            "error": f"pytds connection failed: {e}",
            "trace": traceback.format_exc(),
        }


def _try_pyodbc_connect(
    host: str,
    port: int,
    username: str,
    password: str,
    database: Optional[str],
    timeout: int,
    driver: Optional[str],
    encrypt: bool,
) -> Dict[str, Any]:
    """Attempt connection using pyodbc"""
    if not pyodbc:
        return {"ok": False, "error": "pyodbc not installed"}
    try:
        conn_str_parts = []
        if driver:
            conn_str_parts.append(f"DRIVER={{{driver}}}")
        else:
            conn_str_parts.append("DRIVER={ODBC Driver 17 for SQL Server}")
        conn_str_parts.append(f"SERVER={host},{port}")
        conn_str_parts.append(f"UID={username}")
        conn_str_parts.append(f"PWD={password}")
        if database:
            conn_str_parts.append(f"DATABASE={database}")
        if encrypt:
            conn_str_parts.append("Encrypt=yes")
        conn_str = ";".join(conn_str_parts)
        conn = pyodbc.connect(conn_str, timeout=int(timeout))
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
            cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return {"ok": True, "method": "pyodbc"}
    except Exception as e:
        return {
            "ok": False,
            "error": f"pyodbc connection failed: {e}",
            "trace": traceback.format_exc(),
        }


def _try_pymssql_connect(
    host: str,
    port: int,
    username: str,
    password: str,
    database: Optional[str],
    timeout: int,
) -> Dict[str, Any]:
    """Attempt connection using pymssql"""
    if not pymssql:
        return {"ok": False, "error": "pymssql not installed"}
    try:
        conn = pymssql.connect(
            server=host,
            port=port,
            user=username,
            password=password,
            database=database,
            timeout=int(timeout),
        )
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
            cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return {"ok": True, "method": "pymssql"}
    except Exception as e:
        return {
            "ok": False,
            "error": f"pymssql connection failed: {e}",
            "trace": traceback.format_exc(),
        }


def mssql_check_credentials(
    host: str,
    username: str,
    password: str,
    port: int = 1433,
    database: Optional[str] = None,
    timeout: int = 5,
    driver: Optional[str] = None,
    encrypt: bool = False,
) -> Dict[str, Any]:
    """
    Verify a single username/password against an MS SQL Server.

    Returns:
      {"success": True, "details": {...}} on success
      {"success": False, "error": "..."} on failure

    Important: This function **does not** perform brute-force. It attempts **one** connection
    using the provided credentials. If you need bulk checks, run them manually and only
    on assets you are authorized to test.
    """
    # Basic validation: host and username required; password may be empty string for some accounts but still allowed
    if not host or not username:
        return {"success": False, "error": "host and username are required"}

    # Port connectivity quick check to fail fast
    try:
        if not _check_port_open(host, port, timeout=min(3, timeout)):
            return {
                "success": False,
                "error": f"TCP connection to {host}:{port} failed or port closed",
            }
    except Exception as e:
        # If socket check raises, continue to attempt driver-level connection; but note the error
        pass

    # Try pytds first (preferred)
    pytds_res = _try_pytds_connect(host, port, username, password, database, timeout)
    if pytds_res.get("ok"):
        return {
            "success": True,
            "details": {"method": "pytds", "host": host, "port": port},
        }
    # If pytds attempted and failed, keep its error for reporting
    errors = []
    if pytds_res.get("error"):
        errors.append(pytds_res.get("error"))

    # Then try pyodbc
    pyodbc_res = _try_pyodbc_connect(
        host, port, username, password, database, timeout, driver, encrypt
    )
    if pyodbc_res.get("ok"):
        return {
            "success": True,
            "details": {"method": "pyodbc", "host": host, "port": port},
        }
    if pyodbc_res.get("error"):
        errors.append(pyodbc_res.get("error"))

    # Finally try pymssql
    pymssql_res = _try_pymssql_connect(
        host, port, username, password, database, timeout
    )
    if pymssql_res.get("ok"):
        return {
            "success": True,
            "details": {"method": "pymssql", "host": host, "port": port},
        }
    if pymssql_res.get("error"):
        errors.append(pymssql_res.get("error"))

    # None succeeded
    return {
        "success": False,
        "error": "authentication failed or no supported DB driver succeeded",
        "details": {"attempts": errors},
    }


# LangChain / DeepAgents wrapper: a simple function that agents can call.
# It intentionally enforces single-pair checking and will refuse to accept lists.
def mssql_tool(
    host: str,
    username: str,
    password: str,
    port: int = 1433,
    database: Optional[str] = None,
    timeout: int = 5,
    driver: Optional[str] = None,
    encrypt: bool = False,
) -> Dict[str, Any]:
    """
    DeepAgents/LangChain-friendly tool. Do NOT pass lists of passwords/usernames.
    This wrapper simply forwards to mssql_check_credentials after validating input types.
    """
    # Defensive checks: ensure types are single values (not lists/iterables)
    if isinstance(username, (list, tuple, set)) or isinstance(
        password, (list, tuple, set)
    ):
        return {
            "success": False,
            "error": "username and password must be single values (no lists)",
        }
    return mssql_check_credentials(
        host=host,
        username=username,
        password=password,
        port=port,
        database=database,
        timeout=timeout,
        driver=driver,
        encrypt=encrypt,
    )


# LangChain tool helper
def make_langchain_tool():
    try:
        from langchain.tools import tool as _lc_tool

        @_lc_tool
        def _wrapped(
            host: str,
            username: str,
            password: str,
            port: int = 1433,
            database: Optional[str] = None,
            timeout: int = 5,
            driver: Optional[str] = None,
            encrypt: bool = False,
        ):
            return mssql_tool(
                host=host,
                username=username,
                password=password,
                port=port,
                database=database,
                timeout=timeout,
                driver=driver,
                encrypt=encrypt,
            )

        return _wrapped
    except Exception:
        return mssql_tool


if __name__ == "__main__":
    # Demo (safe defaults: single attempt only)
    import json
    from getpass import getpass

    print(
        "MSSQL credential check demo (safe defaults — single attempt, no brute-force)"
    )
    host = input("Host (IP/hostname): ").strip()
    port_raw = input("Port [1433]: ").strip()
    port = int(port_raw) if port_raw else 1433
    user = input("Username: ").strip()
    pwd = getpass("Password (input hidden): ")
    db = input("Database (optional): ").strip() or None

    print(
        "\nAttempting credential check using available drivers (pytds -> pyodbc -> pymssql)...\n"
    )
    result = mssql_check_credentials(
        host=host, username=user, password=pwd, port=port, database=db, timeout=5
    )
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
