"""
Safer MS SQL credential-check tool for DeepAgents / LangChain

This file implements a LangChain/DeepAgents-compatible tool that **verifies a single
username/password pair** against a Microsoft SQL Server instance. It is intentionally
limited to a single credential check to avoid providing brute-force capability.

DO NOT USE THIS TOOL TO ATTEMPT UNAUTHORIZED ACCESS — use only on systems you own
or have explicit permission to test.

Dependencies (choose one of the below):
  - pyodbc  (recommended)
  - pymssql

Example usage:
  res = mssql_check_credentials(host='10.0.0.5', port=1433, username='sa', password='P@ssw0rd')

Return value: dict with keys: success (bool), error (str, optional), details (dict, optional)

This is safe for integrating into an agent because it requires the agent to provide a
specific username/password pair; it will NOT iterate over lists, threads or do "brute force".
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import socket

# Attempt to prefer pyodbc; fallback to pymssql if pyodbc not available.
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


def mssql_check_credentials(
    host: str,
    username: str,
    password: str,
    port: int = 1433,
    database: Optional[str] = None,
    timeout: int = 5,
    driver: Optional[
        str
    ] = None,  # pyodbc driver name (eg. 'ODBC Driver 17 for SQL Server')
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
    if not host or not username:
        return {"success": False, "error": "host and username are required"}

    if not _check_port_open(host, port, timeout=min(3, timeout)):
        return {
            "success": False,
            "error": f"TCP connection to {host}:{port} failed or port closed",
        }

    # Try pyodbc first
    if pyodbc is not None:
        conn_str_parts = []
        # If a driver name is provided, use it; otherwise let pyodbc choose default
        if driver:
            conn_str_parts.append(f"DRIVER={{{driver}}}")
        else:
            # Common default driver string that often works on modern systems; optional
            conn_str_parts.append("DRIVER={ODBC Driver 17 for SQL Server}")

        conn_str_parts.append(f"SERVER={host},{port}")
        conn_str_parts.append(f"UID={username}")
        conn_str_parts.append(f"PWD={password}")
        if database:
            conn_str_parts.append(f"DATABASE={database}")
        if encrypt:
            conn_str_parts.append("Encrypt=yes")
        conn_str = ";".join(conn_str_parts)

        try:
            conn = pyodbc.connect(conn_str, timeout=timeout)
            try:
                cursor = conn.cursor()
                # A lightweight query to ensure authentication succeeded and DB is responsive
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                cursor.close()
            finally:
                conn.close()

            return {
                "success": True,
                "details": {"method": "pyodbc", "host": host, "port": port},
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"authentication failed or connection error (pyodbc): {e}",
            }

    # Fallback to pymssql
    if pymssql is not None:
        try:
            conn = pymssql.connect(
                server=host,
                port=port,
                user=username,
                password=password,
                database=database,
                timeout=timeout,
            )
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                _ = cursor.fetchone()
                cursor.close()
            finally:
                conn.close()
            return {
                "success": True,
                "details": {"method": "pymssql", "host": host, "port": port},
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"authentication failed or connection error (pymssql): {e}",
            }

    return {
        "success": False,
        "error": "neither pyodbc nor pymssql is installed in the environment",
    }


# LangChain / DeepAgents wrapper: a simple function that agents can call.
# It intentionally enforces single-pair checking and will refuse to accept lists.
def mssql_tool() -> Dict[str, Any]:
    """
    DeepAgents/LangChain-friendly tool. Do NOT pass lists of passwords/usernames.
    """


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

        return _wrapped
    except Exception:
        return mssql_check_credentials


if __name__ == "__main__":
    # Demo (will fail if libraries or server not present)
    print(mssql_check_credentials("127.0.0.1", "sa", "wrong-password"))
