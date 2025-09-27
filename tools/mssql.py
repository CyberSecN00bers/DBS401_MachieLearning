"""
MS SQL Server inspection tool (agent-driven queries)

This file implements the safety-first approach to allow an agent to provide SQL queries
or high-level intents. It focuses on validating agent-supplied SQL and executing it
in a transaction sandbox (with ROLLBACK) unless explicitly allowed.

Security: Read the module docstring in the canvas before enabling agent-driven SQL execution.
"""

from __future__ import annotations

import pyodbc
import traceback
import re
from typing import List, Optional, Dict, Any, Tuple


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
    """Return (is_safe, reasons) — conservative checks.

    This checks for forbidden tokens and naive whitelist enforcement. It is NOT perfect but
    prevents the most obvious destructive queries.
    """
    reasons = []
    if not sql or not sql.strip():
        return False, ["empty query"]

    if _FORBIDDEN_RE.search(sql):
        reasons.append("contains forbidden keywords or commands")

    # Whitelist checks (optional)
    if allowed_schemas:
        # if query mentions schema.table, ensure schema in allowed_schemas
        for match in re.finditer(r"([\w]+)\.[\w]+", sql):
            sch = match.group(1)
            if sch not in allowed_schemas:
                reasons.append(f"schema '{sch}' not in allowed_schemas")

    if allowed_tables:
        # naive check omitted — recommend relying on forbidden keywords and whitelists
        pass

    is_safe = len(reasons) == 0
    return is_safe, reasons


def _safe_execute_with_rollback(
    conn: pyodbc.Connection,
    sql: str,
    params: Optional[Tuple] = None,
    max_rows: Optional[int] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    cur = conn.cursor()
    try:
        # Ensure we are in a transaction sandbox
        conn.autocommit = False
        if timeout:
            # pyodbc allows setting timeout on cursor
            cur.timeout = timeout
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        cols = [column[0] for column in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows) if max_rows else cur.fetchall()
        result = {"columns": cols, "rows": [list(r) for r in rows]}
    except Exception as e:
        result = {"error": str(e), "trace": traceback.format_exc()}
    finally:
        try:
            conn.rollback()  # rollback any changes
        except Exception:
            pass
        try:
            conn.autocommit = True
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

    Default safe behavior: dry_run=True and allow_agent_sql=False. To let agent run queries,
    set allow_agent_sql=True and dry_run=False (and consider allow_destructive=False still).
    """
    server = f"{host},{port}" if port else host
    if trusted_connection:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database or 'master'};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database or 'master'};UID={username};PWD={password};"

    out: Dict[str, Any] = {
        "connection": "REDACTED" if not trusted_connection else conn_str,
        "planned": [],
        "executed": [],
        "errors": [],
    }

    try:
        conn = pyodbc.connect(conn_str, timeout=timeout_seconds or 30)
    except Exception as e:
        return {
            "success": False,
            "error": "failed to connect",
            "details": str(e),
            "trace": traceback.format_exc(),
        }

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


# Backward-compatible small helper if you prefer the older function name
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
