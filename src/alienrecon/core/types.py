"""
Shared types for Alien Recon tool results and core data structures.

ToolResult: Standard result schema for all tool wrappers.
Import and use this in all tool classes and tests to ensure consistency.
"""

from enum import Enum
from typing import Any, Literal, Optional, TypedDict


class ErrorCategory(Enum):
    """Categories for different types of errors."""

    NETWORK = "network"
    PERMISSION = "permission"
    TOOL_MISSING = "tool_missing"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    PARSING = "parsing"


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ToolResult(TypedDict, total=False):
    tool_name: str
    status: Literal["success", "failure", "partial"]
    scan_summary: str
    error: Optional[str]
    findings: Any
    raw_stdout: Optional[str]
    raw_stderr: Optional[str]
