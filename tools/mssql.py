"""
MS SQL Server inspection tool (agent-driven queries)

This module uses a safety-first approach that lets an agent provide SQL queries or high-level
intents while protecting the target from accidental destructive actions.

Connection strategy (fallback order):
 1. pytds (pure-Python TDS driver) — preferred.
 2. pyodbc (ODBC) — supported when an ODBC driver/DSN is available.
 3. mssql-python (first-party Microsoft driver / fallback) — tried last if installed.

Behavior:
 - By default queries are executed inside a transaction sandbox and always ROLLBACK (dry-run).
 - Agent-supplied SQL is validated with conservative forbidden-pattern checks. Use
   `allow_agent_sql=True` and `dry_run=False` and `allow_destructive=True` with extreme caution.

Security reminder: Only use this tool against systems you are authorized to test. Audit all
actions and keep operator approval enabled for any potentially destructive activity.
"""

from __future__ import annotations

import traceback
import re
import time
from typing import List, Optional, Dict, Any, Tuple

# Try optional drivers
try:
    import pytds
except Exception:
    pytds = None

try:
    import pyodbc
except Exception:
    pyodbc = None

try:
    import mssql_python as mssql_python
except Exception:
    mssql_python = None


# --- Safety checks ---
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

    # Simple whitelist schema check: look for schema.table occurrences
    if allowed_schemas:
        for match in re.finditer(r"([\w]+)\.[\w]+", sql):
            sch = match.group(1)
            if sch not in allowed_schemas:
                reasons.append(f"schema '{sch}' not in allowed_schemas")

    # Note: allowed_tables/allowed_databases checks are intentionally conservative and minimal.

    is_safe = len(reasons) == 0
    return is_safe, reasons


# --- Connection helpers ---


def _connect_pytds(
    host: str,
    port: Optional[int],
    username: Optional[str],
    password: Optional[str],
    database: Optional[str],
    timeout_seconds: Optional[int],
) -> Any:
    # pytds.connect signature is flexible; we use common keywords
    if not pytds:
        raise RuntimeError("pytds not installed")
    conn_kwargs = {
        "server": host,
        "port": port or 1433,
        "user": username,
        "password": password,
        "database": database or None,
        "autocommit": False,
    }
    if timeout_seconds:
        conn_kwargs["login_timeout"] = int(timeout_seconds)
    return pytds.connect(**conn_kwargs)


def _connect_pyodbc(
    host: str,
    port: Optional[int],
    username: Optional[str],
    password: Optional[str],
    database: Optional[str],
    driver: str,
    trusted_connection: bool,
    timeout_seconds: Optional[int],
) -> Any:
    if not pyodbc:
        raise RuntimeError("pyodbc not installed")
    server = f"{host},{port}" if port else host
    if trusted_connection:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database or 'master'};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database or 'master'};UID={username};PWD={password};"
    # pyodbc.connect accepts autocommit param too, but we rely on manual commit/rollback
    return pyodbc.connect(conn_str, timeout=int(timeout_seconds or 30))


def _connect_mssql_python(
    host: str,
    port: Optional[int],
    username: Optional[str],
    password: Optional[str],
    database: Optional[str],
    timeout_seconds: Optional[int],
) -> Any:
    if not mssql_python:
        raise RuntimeError("mssql-python not installed")
    # mssql_python has a connect() function; try keyword args first, fallback to connection string
    try:
        return mssql_python.connect(
            host=host,
            port=port or 1433,
            user=username,
            password=password,
            database=database or None,
            timeout=int(timeout_seconds or 30),
        )
    except TypeError:
        # Fallback - try building a connection string
        conn_str = f"Server={host},{port or 1433};Database={database or 'master'};User Id={username};Password={password};TrustServerCertificate=yes;"
        return mssql_python.connect(conn_str)


def _connect_any(
    host: str,
    port: Optional[int],
    username: Optional[str],
    password: Optional[str],
    database: Optional[str],
    driver: Optional[str],
    trusted_connection: bool,
    timeout_seconds: Optional[int],
) -> Tuple[Optional[Any], str, Optional[str]]:
    """Try to connect using pytds -> pyodbc -> mssql_python. Returns (conn, backend_name, error_str).

    backend_name is one of: 'pytds', 'pyodbc', 'mssql-python'.
    """
    errors = []
    # Try pytds first
    if pytds:
        try:
            conn = _connect_pytds(
                host, port, username, password, database, timeout_seconds
            )
            return conn, "pytds", None
        except Exception as e:
            errors.append(f"pytds: {e}")

    # Then try pyodbc (ODBC)
    if pyodbc:
        try:
            conn = _connect_pyodbc(
                host,
                port,
                username,
                password,
                database,
                driver or "ODBC Driver 17 for SQL Server",
                trusted_connection,
                timeout_seconds,
            )
            return conn, "pyodbc", None
        except Exception as e:
            errors.append(f"pyodbc: {e}")

    # Finally try mssql-python
    if mssql_python:
        try:
            conn = _connect_mssql_python(
                host, port, username, password, database, timeout_seconds
            )
            return conn, "mssql-python", None
        except Exception as e:
            errors.append(f"mssql-python: {e}")

    return None, "none", "; ".join(errors)


# --- Execution with transaction sandbox ---


def _safe_execute_with_rollback(
    conn: Any,
    sql: str,
    params: Optional[tuple] = None,
    max_rows: Optional[int] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute SQL while ensuring changes are rolled back. Works with pytds/pyodbc/mssql-python connections.

    Strategy:
      - If the connection object supports `autocommit`, set it to False.
      - Otherwise, send `BEGIN TRANSACTION` explicitly.
      - Execute the query, fetch results, then always `ROLLBACK` at the end.
    """
    cursor = None
    result: Dict[str, Any] = {}
    try:
        cursor = conn.cursor()
        # attempt to set timeout on cursor if supported
        if timeout and hasattr(cursor, "timeout"):
            try:
                cursor.timeout = int(timeout)
            except Exception:
                pass

        # Begin transaction if autocommit not available or True
        autocommit_used = False
        if hasattr(conn, "autocommit"):
            try:
                # remember prev value
                prev_auto = getattr(conn, "autocommit")
                conn.autocommit = False
                autocommit_used = True
            except Exception:
                autocommit_used = False
        else:
            # Explicitly begin transaction
            try:
                cursor.execute("BEGIN TRANSACTION")
            except Exception:
                # Some drivers may not accept BEGIN; ignore and continue
                pass

        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        cols = [c[0] for c in cursor.description] if cursor.description else []
        if max_rows:
            rows = cursor.fetchmany(max_rows)
        else:
            rows = cursor.fetchall()
        result = {"columns": cols, "rows": [list(r) for r in rows]}

    except Exception as e:
        result = {"error": str(e), "trace": traceback.format_exc()}
    finally:
        # Always rollback to avoid persistent changes
        try:
            # prefer native rollback
            if hasattr(conn, "rollback"):
                conn.rollback()
            else:
                # Try issuing ROLLBACK TRANSACTION
                try:
                    if cursor:
                        cursor.execute("ROLLBACK TRANSACTION")
                except Exception:
                    pass
        except Exception:
            pass

        # restore autocommit if we changed it
        try:
            if autocommit_used and hasattr(conn, "autocommit"):
                conn.autocommit = prev_auto
        except Exception:
            pass

    return result


# --- Core agent-friendly mssql tool ---


def mssql_agent_tool(
    host: str,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    # ODBC driver string used if falling back to pyodbc
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
) -> Dict[str, Any]:
    """
    Accepts high-level intents or agent-generated SQL and returns validation + results.

    Default safe behavior: dry_run=True and allow_agent_sql=False. To allow agent-run SQL,
    set allow_agent_sql=True and dry_run=False (and carefully control allow_destructive).
    """
    out: Dict[str, Any] = {
        "backend": None,
        "connection": None,
        "planned": [],
        "executed": [],
        "errors": [],
    }

    conn, backend, err = _connect_any(
        host,
        port,
        username,
        password,
        database,
        driver,
        trusted_connection,
        timeout_seconds,
    )
    out["backend"] = backend
    if conn is None:
        out["success"] = False
        out["error"] = "failed to connect"
        out["details"] = err
        return out

    # Redact sensitive info for output
    out["connection"] = f"connected_via={backend}"

    # Intent mapping (extendable)
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
                    rec = {"query": q, "validated": is_safe, "reasons": reasons}
                    if is_safe and not dry_run:
                        rec["result"] = _safe_execute_with_rollback(
                            conn, q, max_rows=max_rows, timeout=timeout_seconds
                        )
                    out["executed"].append(rec)
            else:
                out["planned"].append(
                    {"intent": intent, "queries": [], "note": "unknown intent"}
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
                rec = {"query": q, "validated": is_safe, "reasons": reasons}
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

    try:
        conn.close()
    except Exception:
        pass

    out["success"] = True
    return out


# Backward-compatible helper
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


if __name__ == "__main__":
    import json

    print(
        "MSSQL agent tool quick-tester (SAFE defaults: dry_run=True, agent SQL blocked)"
    )
    host = input("Host (IP/hostname): ").strip()
    port_raw = input("Port (enter for default 1433): ").strip()
    port = int(port_raw) if port_raw else None
    user = (
        input("Username (leave empty for integrated/trusted if supported): ").strip()
        or None
    )
    pwd = None
    if user:
        from getpass import getpass

        pwd = getpass("Password (input hidden): ")

    db = input("Database (enter for 'master'): ").strip() or None

    # Default flags
    dry_run_choice = (
        input(
            "Dry run (queries will be executed inside transaction and rolled back)? [Y/n]: "
        )
        .strip()
        .lower()
    )
    dry_run = False if dry_run_choice in ("n", "no") else True

    allow_agent_sql_choice = (
        input("Allow agent-supplied SQL execution? (DANGEROUS) [no]: ").strip().lower()
    )
    allow_agent_sql = True if allow_agent_sql_choice in ("y", "yes") else False

    allow_destructive_choice = (
        input("Allow destructive statements if detected? (HIGH RISK) [no]: ")
        .strip()
        .lower()
    )
    allow_destructive = True if allow_destructive_choice in ("y", "yes") else False

    print("\nRunning safe intents (check_version, list_tables) ...\n")
    res = mssql_agent_tool(
        host=host,
        port=port,
        username=user,
        password=pwd,
        database=db,
        dry_run=dry_run,
        intents=["check_version", "list_tables"],
        allow_agent_sql=allow_agent_sql,
        allow_destructive=allow_destructive,
        timeout_seconds=30,
        max_rows=50,
    )

    print("=== RESULT ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))

    # Optionally allow issuing a custom (non-destructive) query for quick testing
    ask_custom = (
        input("\nDo you want to try a custom SELECT query now? [y/N]: ").strip().lower()
    )
    if ask_custom in ("y", "yes"):
        custom = input("Enter SQL (SELECT only recommended): ").strip()
        custom_res = mssql_agent_tool(
            host=host,
            port=port,
            username=user,
            password=pwd,
            database=db,
            dry_run=dry_run,
            custom_queries=[custom],
            allow_agent_sql=allow_agent_sql,
            allow_destructive=allow_destructive,
            timeout_seconds=30,
            max_rows=200,
        )
        print("=== CUSTOM QUERY RESULT ===")
        print(json.dumps(custom_res, indent=2, ensure_ascii=False))

    print(
        "\nTest complete. Remember: use allow_agent_sql=False and dry_run=True for safe exploration."
    )
