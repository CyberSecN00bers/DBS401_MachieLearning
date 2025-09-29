"""
MS SQL Server inspection tool (agent-driven queries)

- Tries pyodbc (ODBC) first.
- Falls back to pymssql if pyodbc fails.
- Falls back to mssql-python (module name: mssql_python) if both above fail.
- Returns 'connection_driver' to show which driver was successful.
- Executes agent-provided queries in a transaction sandbox (ROLLBACK) unless explicitly allowed.

Security: Default safe behavior remains (dry_run=True, allow_agent_sql=False). Only enable agent-driven execution
after reading and accepting the security implications.
"""

from __future__ import annotations

import traceback
import re
import typing as _t
from typing import List, Optional, Dict, Any, Tuple

# Try imports (drivers)
try:
    import pyodbc  # type: ignore
except Exception:
    pyodbc = None  # type: ignore

try:
    import pymssql  # type: ignore
except Exception:
    pymssql = None  # type: ignore

# mssql-python (PyPI: mssql-python) provides `connect` in module `mssql_python`
try:
    import mssql_python  # type: ignore
except Exception:
    mssql_python = None  # type: ignore


# --- Helpers & safety checks ---
_FORBIDDEN_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bBACKUP\b",
    r"\bRESTORE\b",
    r"\bBULK\s+INSERT\b",
    r"\bxp_cmdshell\b",
    r"\bsp_configure\b",
    r"\bsp_start_job\b",
    r"\bsp_stop_job\b",
    r"\bOPENROWSET\b",
]
_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN_PATTERNS), re.IGNORECASE)


def _is_safe_query(
    sql: str,
    allowed_schemas: Optional[List[str]] = None,
    allowed_databases: Optional[List[str]] = None,
    allowed_tables: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if not sql or not sql.strip():
        return False, ["empty query"]

    if _FORBIDDEN_RE.search(sql):
        reasons.append("contains forbidden keywords or commands")

    # Whitelist checks (optional)
    if allowed_schemas:
        for match in re.finditer(r"([\w]+)\.[\w]+", sql):
            sch = match.group(1)
            if sch not in allowed_schemas:
                reasons.append(f"schema '{sch}' not in allowed_schemas")

    if allowed_tables:
        # Not implemented deep check; keep conservative.
        pass

    return (len(reasons) == 0), reasons


def _safe_execute_with_rollback(
    conn: Any,
    sql: str,
    params: Optional[Tuple] = None,
    max_rows: Optional[int] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute SQL in transaction sandbox and attempt ROLLBACK.
    Compatible with pyodbc, pymssql, mssql-python (DB-API-like).
    """
    cur = None
    try:
        cur = conn.cursor()

        # Try to disable autocommit if available
        try:
            if hasattr(conn, "autocommit"):
                # pyodbc: conn.autocommit = False
                # some drivers might expose method as well
                try:
                    conn.autocommit = False
                except Exception:
                    try:
                        conn.autocommit(False)  # type: ignore
                    except Exception:
                        pass
        except Exception:
            pass

        # Cursor timeout (pyodbc supports)
        if timeout is not None:
            try:
                if hasattr(cur, "timeout"):
                    cur.timeout = timeout  # pyodbc
            except Exception:
                pass

        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)

        cols = []
        try:
            if getattr(cur, "description", None):
                cols = [c[0] for c in cur.description]
        except Exception:
            cols = []

        # Fetch rows safely
        rows = []
        try:
            if max_rows:
                try:
                    rows = cur.fetchmany(max_rows)
                except Exception:
                    rows = cur.fetchall()[:max_rows]
            else:
                rows = cur.fetchall()
        except Exception:
            rows = []

        return {"columns": cols, "rows": [list(r) for r in rows]}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}
    finally:
        # Always try to rollback to avoid side effects
        try:
            if hasattr(conn, "rollback"):
                conn.rollback()
        except Exception:
            pass

        # Try to restore autocommit True if possible
        try:
            if hasattr(conn, "autocommit"):
                try:
                    conn.autocommit = True
                except Exception:
                    try:
                        conn.autocommit(True)  # type: ignore
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass


# --- Core agent-friendly mssql tool ---


def mssql_agent_tool(
    host: str,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    driver: str = "ODBC Driver 17 for SQL Server",
    trusted_connection: bool = False,
    # agent-driven params
    allow_agent_sql: bool = False,
    custom_queries: Optional[List[str]] = None,
    intents: Optional[List[str]] = None,
    dry_run: bool = True,
    allowed_schemas: Optional[List[str]] = None,
    allowed_databases: Optional[List[str]] = None,
    allowed_tables: Optional[List[str]] = None,
    max_rows: Optional[int] = 1000,
    timeout_seconds: Optional[int] = 30,
    allow_destructive: bool = False,
    preferred_driver: str = "auto",  # "auto", "pyodbc", "pymssql", "mssql_python"
) -> Dict[str, Any]:
    """
    Accepts high-level intents or agent-generated SQL and returns validation + results.

    preferred_driver: choose driver explicitly, or 'auto' for fallback sequence.
    """
    server = f"{host},{port}" if port else host

    # Build connection strings:
    # pyodbc: DRIVER={...};SERVER=host,port;DATABASE=...;UID=...;PWD=...
    pyodbc_conn_str = None
    if not trusted_connection:
        pyodbc_conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database or 'master'};UID={username};PWD={password};"
    else:
        pyodbc_conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database or 'master'};Trusted_Connection=yes;"

    # mssql-python expects a SQL connection string like "Server=...;Database=...;UID=...;PWD=...;"
    mssql_python_conn_str = f"Server={host};Database={database or 'master'};"
    if port:
        # mssql-python typically accepts "Server=host,port" or separate; include port with host for safety
        mssql_python_conn_str = f"Server={host},{port};Database={database or 'master'};"
    if trusted_connection:
        mssql_python_conn_str += "Trusted_Connection=yes;"
    else:
        if username is not None:
            mssql_python_conn_str += f"UID={username};PWD={password or ''};"

    out: Dict[str, Any] = {
        "connection": "REDACTED",
        "connection_driver": None,
        "planned": [],
        "executed": [],
        "errors": [],
    }

    conn = None
    used_driver = None

    # Helper to try connecting with given driver string
    def try_pyodbc():
        nonlocal conn, used_driver
        if pyodbc is None:
            out["errors"].append("pyodbc not installed")
            return False
        try:
            conn_local = pyodbc.connect(pyodbc_conn_str, timeout=timeout_seconds or 30)
            conn = conn_local
            used_driver = "pyodbc"
            out["connection"] = f"pyodbc://{server}"
            out["connection_driver"] = used_driver
            return True
        except Exception as e:
            out["errors"].append(f"pyodbc connection failed: {e}")
            return False

    def try_pymssql():
        nonlocal conn, used_driver
        if pymssql is None:
            out["errors"].append("pymssql not installed")
            return False
        try:
            # pymssql.connect accepts server, user, password, database, port=...
            conn_local = pymssql.connect(
                server=host,
                user=username or "",
                password=password or "",
                database=database or "master",
                port=port,
                login_timeout=timeout_seconds or 30,
            )
            conn = conn_local
            used_driver = "pymssql"
            out["connection"] = f"pymssql://{server}"
            out["connection_driver"] = used_driver
            return True
        except Exception as e:
            out["errors"].append(f"pymssql connection failed: {e}")
            return False

    def try_mssql_python():
        nonlocal conn, used_driver
        if mssql_python is None:
            out["errors"].append("mssql_python (mssql-python) not installed")
            return False
        try:
            # mssql_python provides connect(conn_string)
            # Pass the mssql-style connection string
            conn_local = mssql_python.connect(mssql_python_conn_str)  # type: ignore
            conn = conn_local
            used_driver = "mssql_python"
            out["connection"] = f"mssql_python://{server}"
            out["connection_driver"] = used_driver
            return True
        except Exception as e:
            out["errors"].append(f"mssql_python connection failed: {e}")
            return False

    # Connection selection logic
    if preferred_driver == "pyodbc":
        if not try_pyodbc():
            return {
                "success": False,
                "error": "pyodbc preferred but connection failed",
                "details": out["errors"],
            }
    elif preferred_driver == "pymssql":
        if not try_pymssql():
            return {
                "success": False,
                "error": "pymssql preferred but connection failed",
                "details": out["errors"],
            }
    elif preferred_driver == "mssql_python":
        if not try_mssql_python():
            return {
                "success": False,
                "error": "mssql_python preferred but connection failed",
                "details": out["errors"],
            }
    else:  # auto fallback: pyodbc -> pymssql -> mssql_python
        if try_pyodbc():
            pass
        elif try_pymssql():
            pass
        elif try_mssql_python():
            pass
        else:
            return {
                "success": False,
                "error": "failed to connect using available drivers (pyodbc, pymssql, mssql_python)",
                "details": out["errors"],
            }

    # Intent map (extendable)
    intent_map = {
        "check_version": ["SELECT @@VERSION AS full_version"],
        "list_databases": ["SELECT name, state_desc FROM sys.databases ORDER BY name"],
        "list_tables": [
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME"
        ],
        "logins": [
            "SELECT principal_id, name, type_desc FROM sys.server_principals ORDER BY name"
        ],
        "agent_jobs": [
            "SELECT job_id, name, enabled FROM msdb.dbo.sysjobs ORDER BY name"
        ],
    }

    # Handle intents
    if intents:
        for intent in intents:
            mapped = intent_map.get(intent)
            if mapped:
                out["planned"].append({"intent": intent, "queries": mapped})
                for q in mapped:
                    is_safe, reasons = _is_safe_query(
                        q, allowed_schemas, allowed_databases, allowed_tables
                    )
                    rec: Dict[str, Any] = {
                        "query": q,
                        "validated": is_safe,
                        "reasons": reasons,
                    }
                    if is_safe and not dry_run:
                        rec["result"] = _safe_execute_with_rollback(
                            conn, q, max_rows=max_rows, timeout=timeout_seconds
                        )
                    out["executed"].append(rec)
            else:
                out["planned"].append(
                    {
                        "intent": intent,
                        "queries": [],
                        "note": "unknown intent — agent should provide SQL or request help",
                    }
                )

    # Handle agent-supplied SQL
    if custom_queries:
        if not allow_agent_sql:
            out["errors"].append("agent-supplied SQL blocked (allow_agent_sql=False)")
        else:
            for q in custom_queries:
                is_safe, reasons = _is_safe_query(
                    q, allowed_schemas, allowed_databases, allowed_tables
                )
                rec: Dict[str, Any] = {
                    "query": q,
                    "validated": is_safe,
                    "reasons": reasons,
                }
                if not is_safe and not allow_destructive:
                    rec["allowed"] = False
                else:
                    rec["allowed"] = True
                    if dry_run:
                        rec["note"] = "dry_run - not executed"
                    else:
                        rec["result"] = _safe_execute_with_rollback(
                            conn, q, max_rows=max_rows, timeout=timeout_seconds
                        )
                out["executed"].append(rec)

    # Close connection
    try:
        conn.close()
    except Exception:
        pass

    out["success"] = True
    return out


# Backward-compatible alias
def mssql_tool(*args, **kwargs):
    return mssql_agent_tool(*args, **kwargs)


# LangChain tool helper
def make_langchain_tool():
    try:
        from langchain.tools import tool as _lc_tool

        @_lc_tool
        def _wrapped(
            host: str,
            port: Optional[int] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            **kwargs,
        ):
            return mssql_agent_tool(
                host=host, port=port, username=username, password=password, **kwargs
            )

        return _wrapped
    except Exception:
        return mssql_agent_tool
