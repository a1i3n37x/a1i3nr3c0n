"""
MCP-based agent implementation for AlienRecon.

This module provides an agent that uses MCP for tool calling,
enabling support for multiple LLM providers.
"""

import asyncio
import json
import logging
import re
from typing import Any, Optional

from rich.console import Console

from ..config import Config
from .mcp_client import MCPClient, MCPToolCall, MCPToolResult, create_mcp_client

logger = logging.getLogger(__name__)
console = Console()


class MCPAgent:
    """Agent that uses MCP for tool interactions."""

    def __init__(self, llm_client: Any, config: Optional[Config] = None):
        """Initialize the MCP agent."""
        self.llm_client = llm_client
        self.config = config or Config()
        self.mcp_client: Optional[MCPClient] = None
        self._tool_call_pattern = re.compile(
            r'```json\s*(\{.*?"tool".*?\})\s*```', re.DOTALL | re.IGNORECASE
        )
        self._system_prompt: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the MCP client and discover servers."""
        self.mcp_client = create_mcp_client()
        await self.mcp_client.discover_servers()

        # Log available tools
        tools = self.mcp_client.get_available_tools()
        logger.info(f"MCP Agent initialized with {len(tools)} available tools")

        # Build dynamic system prompt from discovered tools
        self._system_prompt = self._build_system_prompt(tools)

    async def process_message(
        self, user_message: str, chat_history: list[dict[str, str]]
    ) -> tuple[str, Optional[MCPToolResult]]:
        """Process a user message and potentially execute tools."""

        # Add user message to history
        messages = (
            [
                {
                    "role": "system",
                    "content": self._system_prompt or self._get_fallback_prompt(),
                }
            ]
            + chat_history
            + [{"role": "user", "content": user_message}]
        )

        # Get LLM response
        response = await self._get_llm_response(messages)

        if not response:
            return "I encountered an error communicating with the AI model.", None

        # Check if response contains a tool call
        tool_call = self._extract_tool_call(response)

        if tool_call:
            # Execute the tool via MCP
            result = await self.mcp_client.call_tool(tool_call)

            # Format tool result for display
            if result.status == "success":
                return self._format_tool_success(tool_call, result), result
            else:
                return self._format_tool_error(tool_call, result), result
        else:
            # Regular conversational response
            return response, None

    def _extract_tool_call(self, response: str) -> Optional[MCPToolCall]:
        """Extract tool call from LLM response."""
        match = self._tool_call_pattern.search(response)
        if match:
            try:
                tool_data = json.loads(match.group(1))
                return MCPToolCall(
                    tool=tool_data.get("tool", ""),
                    parameters=tool_data.get("parameters", {}),
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool call JSON: {e}")
                return None
        return None

    async def _get_llm_response(self, messages: list[dict[str, str]]) -> Optional[str]:
        """Get response from the LLM."""
        try:
            # This is a simplified version - in practice, you'd handle different
            # LLM providers (OpenAI, Claude, local models) based on config

            if hasattr(self.llm_client, "chat"):
                # OpenAI-style client
                response = await asyncio.to_thread(
                    self.llm_client.chat.completions.create,
                    model=self.config.model or "gpt-4",
                    messages=messages,
                    temperature=0.4,
                )
                return response.choices[0].message.content
            else:
                # Add support for other LLM providers here
                logger.error("Unsupported LLM client type")
                return None

        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            return None

    def _format_tool_success(
        self, tool_call: MCPToolCall, result: MCPToolResult
    ) -> str:
        """Format successful tool execution for display."""
        output = f"[green]✓ Executed {tool_call.tool}[/green]\n\n"

        if isinstance(result.result, dict):
            output += json.dumps(result.result, indent=2)
        else:
            output += str(result.result)

        if result.metadata:
            output += f"\n\n[dim]Execution time: {result.metadata.get('execution_time', 'N/A')}s[/dim]"

        return output

    def _format_tool_error(self, tool_call: MCPToolCall, result: MCPToolResult) -> str:
        """Format tool execution error for display."""
        output = f"[red]✗ Error executing {tool_call.tool}[/red]\n\n"
        output += f"Error: {result.error}\n\n"
        output += "[yellow]Troubleshooting suggestions:[/yellow]\n"

        # Add context-specific error guidance
        if "not found" in result.error.lower():
            output += "- Ensure the MCP server for this tool is running\n"
            output += "- Check if the tool is properly installed\n"
        elif "connection" in result.error.lower():
            output += "- Verify network connectivity\n"
            output += "- Check if the target is reachable\n"

        return output

    def _build_system_prompt(self, tools: list[dict[str, Any]]) -> str:
        """Build dynamic system prompt from discovered tools."""
        prompt = """You are Alien Recon, an AI assistant from Alien37.com specializing in CTF challenges and security assessments.

**IMPORTANT MCP MODE**: You are operating in Model Context Protocol (MCP) mode. To use tools, you must include tool calls in your response using this exact format:

<tool_call>
{
    "tool": "tool_name",
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    }
}
</tool_call>

The JSON must be wrapped in <tool_call> tags, NOT in code blocks.

Available tools:
"""

        # Group tools by category
        categories = {}
        for tool in tools:
            category = tool.get("category", "Uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(tool)

        # Build tool documentation
        for category, category_tools in sorted(categories.items()):
            prompt += f"\n## {category}\n"
            for tool in sorted(category_tools, key=lambda t: t["name"]):
                prompt += f"- {tool['name']}: {tool['description']}\n"

                # Add parameter documentation
                params = tool.get("parameters", {})
                if params:
                    required_params = []
                    optional_params = []

                    for param_name, param_info in params.items():
                        param_desc = f"{param_name}"
                        if param_info.get("required"):
                            required_params.append(param_desc)
                        else:
                            optional_params.append(param_desc)

                    param_list = []
                    if required_params:
                        param_list.extend([f"{p} (required)" for p in required_params])
                    param_list.extend(optional_params)

                    if param_list:
                        prompt += f"  Parameters: {', '.join(param_list)}\n"
                prompt += "\n"

        prompt += """
Your primary directive is to assist ONLY with ethical hacking tasks for which the user has explicit permission (like CTF platforms).

When the user asks you to perform reconnaissance:
1. First explain what you're going to do and why
2. Then provide the JSON tool call in the format above
3. After receiving results, analyze them and suggest next steps
4. Maintain momentum - keep pushing forward when paths are found

Remember:
- Start with broad scans (nmap) to identify services
- Use targeted tools based on discovered services
- Provide educational explanations about your choices
- Only use tools on authorized targets

If a tool returns an error, suggest alternatives or troubleshooting steps.

**EXAMPLE CORRECT RESPONSE**:
"I'll help you scan the target. Let me start with a basic nmap scan to identify open ports.

<tool_call>
{
    "tool": "nmap_scan",
    "parameters": {
        "target": "127.0.0.1",
        "scan_type": "stealth",
        "ports": "1-1000"
    }
}
</tool_call>

This will perform a stealth SYN scan on the top 1000 ports."""

        return prompt

    def _get_fallback_prompt(self) -> str:
        """Get fallback prompt if dynamic discovery fails."""
        return """You are Alien Recon, an AI assistant from Alien37.com specializing in CTF challenges and security assessments.

**IMPORTANT**: You are operating in MCP (Model Context Protocol) mode. Tools should be available but discovery may have failed.

To use tools, respond with a JSON block in this format:
<tool_call>
{
    "tool": "tool_name",
    "parameters": {
        "param1": "value1"
    }
}
</tool_call>

Common tools include: nmap_scan, nikto_scan, ffuf_directory_enumeration, searchsploit_query, and others.

If you receive an error about a tool not being found, it may not be available in this session."""

    async def close(self) -> None:
        """Clean up resources."""
        if self.mcp_client:
            await self.mcp_client.close()
