"""
Audit logging service for penetration testing activities.

This module provides comprehensive audit trail functionality to track all
security testing activities with timestamps, user actions, and tool invocations.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum


class AuditEventType(Enum):
    """Types of events that can be audited"""
    SCAN_START = "scan_start"
    SCAN_END = "scan_end"
    TOOL_INVOCATION = "tool_invocation"
    TOOL_RESULT = "tool_result"
    HUMAN_DECISION = "human_decision"
    ERROR = "error"
    WARNING = "warning"
    CREDENTIAL_ACCESS = "credential_access"
    DATABASE_QUERY = "database_query"
    SYSTEM_CHANGE = "system_change"


class AuditLogger:
    """
    Comprehensive audit logging for penetration testing activities.
    
    All events are logged with timestamps and written to a JSONL file
    for tamper-evident audit trails.
    """
    
    def __init__(self, audit_file: str = "audit.jsonl", log_dir: str = "logs"):
        """
        Initialize the audit logger.
        
        Args:
            audit_file: Name of the audit log file
            log_dir: Directory to store audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamped audit file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audit_file = self.log_dir / f"audit_{timestamp}.jsonl"
        
        self.logger = logging.getLogger(__name__)
        self.session_id = timestamp
        
        # Log session start
        self._write_event({
            "event_type": "session_start",
            "session_id": self.session_id,
            "timestamp": self._get_timestamp()
        })
    
    def _get_timestamp(self) -> str:
        """Get ISO format timestamp"""
        return datetime.utcnow().isoformat() + "Z"
    
    def _write_event(self, event: Dict[str, Any]) -> None:
        """
        Write an event to the audit log file.
        
        Args:
            event: Event dictionary to log
        """
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                json.dump(event, f)
                f.write('\n')
        except Exception as e:
            self.logger.error(f"Failed to write audit event: {e}")
    
    def log_event(
        self,
        event_type: AuditEventType,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
        target: Optional[str] = None
    ) -> None:
        """
        Log a security testing event.
        
        Args:
            event_type: Type of event being logged
            description: Human-readable description
            details: Additional structured details
            user: User performing the action
            target: Target system/host being tested
        """
        event = {
            "timestamp": self._get_timestamp(),
            "session_id": self.session_id,
            "event_type": event_type.value,
            "description": description,
            "user": user or "system",
            "target": target,
            "details": details or {}
        }
        
        self._write_event(event)
        self.logger.info(f"Audit: {event_type.value} - {description}")
    
    def log_tool_invocation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        target: str,
        approved_by: Optional[str] = None
    ) -> None:
        """
        Log a tool invocation with full details.
        
        Args:
            tool_name: Name of the tool being invoked
            arguments: Arguments passed to the tool
            target: Target system
            approved_by: User who approved the action
        """
        self.log_event(
            AuditEventType.TOOL_INVOCATION,
            f"Tool invoked: {tool_name}",
            details={
                "tool": tool_name,
                "arguments": arguments,
                "approved_by": approved_by
            },
            target=target
        )
    
    def log_tool_result(
        self,
        tool_name: str,
        success: bool,
        result_summary: str,
        target: str
    ) -> None:
        """
        Log tool execution results.
        
        Args:
            tool_name: Name of the tool
            success: Whether execution was successful
            result_summary: Summary of results
            target: Target system
        """
        self.log_event(
            AuditEventType.TOOL_RESULT,
            f"Tool completed: {tool_name}",
            details={
                "tool": tool_name,
                "success": success,
                "result_summary": result_summary
            },
            target=target
        )
    
    def log_human_decision(
        self,
        decision: str,
        context: str,
        user: str
    ) -> None:
        """
        Log human-in-the-loop decisions.
        
        Args:
            decision: The decision made (accept/reject/edit)
            context: Context of the decision
            user: User who made the decision
        """
        self.log_event(
            AuditEventType.HUMAN_DECISION,
            f"Human decision: {decision}",
            details={
                "decision": decision,
                "context": context
            },
            user=user
        )
    
    def log_database_query(
        self,
        query: str,
        database: str,
        target: str,
        read_only: bool = True
    ) -> None:
        """
        Log database query execution.
        
        Args:
            query: SQL query executed
            database: Database name
            target: Target host
            read_only: Whether query was read-only
        """
        self.log_event(
            AuditEventType.DATABASE_QUERY,
            f"Database query executed",
            details={
                "query": query[:200],  # Truncate long queries
                "database": database,
                "read_only": read_only
            },
            target=target
        )
    
    def log_error(
        self,
        error_message: str,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log errors and exceptions.
        
        Args:
            error_message: Error description
            exception: Exception object if available
            context: Additional context
        """
        details = context or {}
        if exception:
            details["exception_type"] = type(exception).__name__
            details["exception_message"] = str(exception)
        
        self.log_event(
            AuditEventType.ERROR,
            error_message,
            details=details
        )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of the current audit session.
        
        Returns:
            Dict with session statistics
        """
        events: List[Dict[str, Any]] = []
        
        try:
            with open(self.audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    events.append(json.loads(line))
        except Exception as e:
            self.logger.error(f"Failed to read audit log: {e}")
            return {}
        
        event_counts = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "session_id": self.session_id,
            "total_events": len(events),
            "event_counts": event_counts,
            "audit_file": str(self.audit_file)
        }
    
    def close_session(self) -> None:
        """Close the audit session"""
        summary = self.get_session_summary()
        self._write_event({
            "event_type": "session_end",
            "timestamp": self._get_timestamp(),
            "summary": summary
        })


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def initialize_audit_logger(audit_file: str = "audit.jsonl", log_dir: str = "logs") -> AuditLogger:
    """
    Initialize the global audit logger.
    
    Args:
        audit_file: Name of the audit log file
        log_dir: Directory to store audit logs
        
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    _audit_logger = AuditLogger(audit_file, log_dir)
    return _audit_logger
