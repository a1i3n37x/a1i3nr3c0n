#!/usr/bin/env python3
"""
Direct test of the validate_and_fix_history function to ensure our fix works.
"""

import json
import logging
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from alienrecon.core.agent import validate_and_fix_history

# Set up logging to capture warnings
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def test_with_fix():
    """Test history with proper tool_calls field (after our fix)."""
    print("=== Test 1: History WITH tool_calls field (after fix) ===")

    history_with_fix = [
        {"role": "user", "content": "Scan 192.168.1.1"},
        {
            "role": "assistant",
            "content": 'I\'ll scan that target.\n\n<tool_call>{"tool": "nmap_scan"}</tool_call>',
            "tool_calls": [
                {
                    "id": "mcp_nmap_scan_12345",
                    "type": "function",
                    "function": {
                        "name": "nmap_scan",
                        "arguments": '{"target": "192.168.1.1"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "mcp_nmap_scan_12345",
            "content": '{"status": "success", "result": "Found 3 ports"}',
        },
    ]

    print("Input history:")
    print(json.dumps(history_with_fix, indent=2))

    print("\nValidating history...")
    fixed = validate_and_fix_history(history_with_fix)

    print(f"\nResult: {len(fixed)} messages retained")
    print("✅ No orphaned tool message warning expected\n")


def test_without_fix():
    """Test history without proper tool_calls field (before our fix)."""
    print("=== Test 2: History WITHOUT tool_calls field (before fix) ===")

    history_without_fix = [
        {"role": "user", "content": "Scan 192.168.1.1"},
        {
            "role": "assistant",
            "content": 'I\'ll scan that target.\n\n<tool_call>{"tool": "nmap_scan"}</tool_call>',
            # Note: NO tool_calls field - this causes orphaned messages
        },
        {
            "role": "tool",
            "tool_call_id": "mcp_nmap_scan_12345",
            "content": '{"status": "success", "result": "Found 3 ports"}',
        },
    ]

    print("Input history:")
    print(json.dumps(history_without_fix, indent=2))

    print("\nValidating history...")
    fixed = validate_and_fix_history(history_without_fix)

    print(f"\nResult: {len(fixed)} messages retained")
    print("❌ Orphaned tool message warning expected above\n")


def test_mixed_history():
    """Test history with multiple tool calls, some with fix, some without."""
    print("=== Test 3: Mixed history ===")

    mixed_history = [
        {"role": "user", "content": "Scan multiple targets"},
        # First tool call WITH fix
        {
            "role": "assistant",
            "content": "Scanning first target",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "nmap_scan", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "{}"},
        # Second tool call WITHOUT fix
        {"role": "assistant", "content": "Scanning second target"},
        {"role": "tool", "tool_call_id": "call_2", "content": "{}"},
        # Third tool call WITH fix
        {
            "role": "assistant",
            "content": "Scanning third target",
            "tool_calls": [
                {
                    "id": "call_3",
                    "type": "function",
                    "function": {"name": "nmap_scan", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_3", "content": "{}"},
    ]

    print("Validating mixed history...")
    fixed = validate_and_fix_history(mixed_history)
    print(f"Result: {len(fixed)} messages retained")
    print("Should see one orphaned message warning for call_2\n")


if __name__ == "__main__":
    print("Testing validate_and_fix_history function\n")

    test_with_fix()
    print("-" * 60)
    test_without_fix()
    print("-" * 60)
    test_mixed_history()

    print("\n✅ Tests complete. Check the output above for warnings.")
