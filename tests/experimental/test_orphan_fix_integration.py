#!/usr/bin/env python3
"""
Integration test to verify the orphaned tool message fix works with the real AlienRecon system.
"""

import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from alienrecon.config import Config
from alienrecon.core.agent import validate_and_fix_history
from alienrecon.core.refactored_session_controller import RefactoredSessionController

# Set up logging to capture warnings
logging.basicConfig(level=logging.WARNING)


class TestOrphanedToolMessageFix(unittest.TestCase):
    """Test that the orphaned tool message warning is fixed."""

    def setUp(self):
        """Set up test environment."""
        # Create a test config
        self.config = Config()
        self.config.openai_api_key = "test-key"

    @patch("alienrecon.core.mcp_server_manager.MCPServerManager")
    @patch("alienrecon.core.mcp_client.MCPClient")
    def test_no_orphaned_messages_with_mcp(self, mock_mcp_client, mock_server_manager):
        """Test that MCP tool calls don't create orphaned messages."""
        # Set up mocks
        mock_server_manager.return_value.start_servers.return_value = True
        mock_server_manager.return_value.stop_servers.return_value = None
        mock_mcp_client.return_value.connect = MagicMock()
        mock_mcp_client.return_value.disconnect = MagicMock()

        # Create session controller
        RefactoredSessionController(self.config)

        # Create test chat history with MCP tool call structure
        # This simulates what happens after our fix is applied
        test_history = [
            {"role": "user", "content": "Scan the target 192.168.1.1"},
            {
                "role": "assistant",
                "content": 'I\'ll scan the target using nmap.\n\n<tool_call>\n{"tool": "nmap_scan", "parameters": {"target": "192.168.1.1"}}\n</tool_call>',
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
                "content": '{"tool": "nmap_scan", "result": {"summary": "Found 3 open ports"}, "status": "success"}',
            },
        ]

        # Try to capture warnings
        try:
            with self.assertLogs(level=logging.WARNING) as log_context:
                # Validate the history - should not produce orphaned message warnings
                fixed_history = validate_and_fix_history(test_history)

                # Check that no orphaned message warnings were logged
                orphan_warnings = [
                    log
                    for log in log_context.output
                    if "orphaned tool message" in log.lower()
                ]

                # Assert no orphaned warnings
                self.assertEqual(
                    len(orphan_warnings),
                    0,
                    f"Found orphaned message warnings: {orphan_warnings}",
                )
        except AssertionError as e:
            if "no logs of level WARNING or higher triggered" in str(e):
                # This is actually what we want - no warnings!
                # Just validate the history without the log context
                fixed_history = validate_and_fix_history(test_history)
            else:
                raise

        # Verify the history is still intact
        self.assertEqual(len(fixed_history), 3)
        self.assertEqual(fixed_history[0]["role"], "user")
        self.assertEqual(fixed_history[1]["role"], "assistant")
        self.assertEqual(fixed_history[2]["role"], "tool")

        # Verify tool_calls field is preserved
        self.assertIn("tool_calls", fixed_history[1])
        self.assertEqual(fixed_history[1]["tool_calls"][0]["id"], "mcp_nmap_scan_12345")

    def test_orphaned_messages_without_fix(self):
        """Test that messages without proper tool_calls field do create warnings."""
        # Create test chat history WITHOUT the fix (no tool_calls field)
        test_history = [
            {"role": "user", "content": "Scan the target 192.168.1.1"},
            {
                "role": "assistant",
                "content": 'I\'ll scan the target using nmap.\n\n<tool_call>\n{"tool": "nmap_scan", "parameters": {"target": "192.168.1.1"}}\n</tool_call>',
                # Note: NO tool_calls field here - this is the bug we fixed
            },
            {
                "role": "tool",
                "tool_call_id": "mcp_nmap_scan_12345",
                "content": '{"tool": "nmap_scan", "result": {"summary": "Found 3 open ports"}, "status": "success"}',
            },
        ]

        # Capture warnings
        with self.assertLogs(level=logging.WARNING) as log_context:
            # Validate the history - SHOULD produce orphaned message warnings
            validate_and_fix_history(test_history)

            # Check that orphaned message warnings WERE logged
            orphan_warnings = [
                log
                for log in log_context.output
                if "orphaned tool message" in log.lower()
            ]

            # Assert we got the orphaned warning
            self.assertGreater(
                len(orphan_warnings),
                0,
                "Expected orphaned message warning but none found",
            )

            # Verify the specific warning message
            self.assertTrue(
                any("mcp_nmap_scan_12345" in log for log in orphan_warnings),
                "Warning should mention the specific tool call ID",
            )


if __name__ == "__main__":
    # Run the tests
    print("=== Testing Orphaned Tool Message Fix ===\n")
    unittest.main(verbosity=2)
