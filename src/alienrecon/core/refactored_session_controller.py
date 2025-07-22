# src/alienrecon/core/refactored_session_controller.py
"""Refactored SessionController using modular architecture."""

import logging
from typing import Any, Optional

from openai.types.chat.chat_completion_message import ChatCompletionMessage

from .agent_factory import AgentFactory
from .cache import ResultCache
from .config import initialize_openai_client
from .exceptions import ConfigurationError, SecurityError, ValidationError
from .interaction_handler import InteractionHandler
from .plan_executor import PlanExecutor
from .session_manager import SessionManager
from .tool_orchestrator import ToolOrchestrator

logger = logging.getLogger(__name__)


class RefactoredSessionController:
    """Refactored session controller with modular architecture."""

    def __init__(self, session_file: Optional[str] = None, dry_run: bool = False):
        """Initialize the session controller with dependency injection."""
        self.interaction = InteractionHandler()
        self.dry_run = dry_run

        try:
            self.openai_client = initialize_openai_client()
            # Initialize MCP Agent for dynamic tool discovery
            self.mcp_agent = None
        except Exception as e:
            self.interaction.display_error(f"Failed to initialize OpenAI client: {e}")
            logger.critical(f"OpenAI initialization failed: {e}", exc_info=True)
            raise ConfigurationError(f"OpenAI initialization failed: {e}")

        # Initialize core modules
        self.cache = ResultCache()
        self.session_manager = SessionManager(session_file)
        self.tool_orchestrator = ToolOrchestrator(self.cache, dry_run=dry_run)
        self.plan_executor = PlanExecutor(self.tool_orchestrator)

        # AI state
        self.is_novice_mode: bool = True

        # Load existing session
        if self.session_manager.load_session():
            pass  # No tool calls to restore in MCP mode

        # Initialize MCP adapter - AlienRecon now uses MCP exclusively
        self.mcp_adapter = None
        self.mcp_enabled = False

        self.interaction.display_info(
            "\n[bold yellow]🔌 Starting Model Context Protocol[/bold yellow]"
        )
        self.interaction.display_info("Initializing MCP server...")

        # Start MCP server automatically
        import asyncio

        from .mcp_server_manager import get_server_manager

        server_manager = get_server_manager()
        try:
            started = asyncio.run(server_manager.start_servers())
            if started:
                self.mcp_enabled = True
                running_servers = server_manager.get_running_servers()
                self.interaction.display_success(
                    f"✅ MCP server started: {', '.join(running_servers)}"
                )
            else:
                self.interaction.display_warning(
                    "⚠️  MCP server failed to start. Some tools may not be available."
                )
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            self.interaction.display_error(f"❌ Failed to start MCP server: {e}")

        # Initialize MCP adapter
        if self.mcp_enabled:
            try:
                from .mcp_session_adapter import MCPSessionAdapter

                self.mcp_adapter = MCPSessionAdapter(self)
                logger.info("Initializing MCP adapter")

                # Initialize MCP adapter (now synchronous)
                self.mcp_adapter.initialize()

                self.interaction.display_success(
                    "✅ MCP adapter initialized successfully"
                )

                # Create and initialize MCP Agent for dynamic tool discovery
                logger.info("Creating MCP Agent with dynamic tool discovery")
                self.mcp_agent = AgentFactory.create_agent(self.openai_client)
                asyncio.run(self.mcp_agent.initialize())

                self.interaction.display_info(
                    "[dim]All tools execute via MCP server[/dim]\n"
                )
            except Exception as e:
                logger.error(f"Failed to initialize MCP adapter: {e}")
                self.interaction.display_error(f"❌ MCP initialization failed: {e}")
                self.mcp_enabled = False

        logger.info("RefactoredSessionController initialized successfully")

    # Target Management
    def set_target(self, target_address: str) -> None:
        """Set the target for reconnaissance."""
        self.session_manager.set_target(target_address)
        self.session_manager.save_session()

        # Get the resolved target for display
        resolved_target = self.session_manager.get_target()
        if resolved_target:
            self.interaction.display_success(f"Target set to: {resolved_target}")

    def get_target(self) -> Optional[str]:
        """Get the current target."""
        return self.session_manager.get_target()

    # Session Management
    def save_session(self) -> None:
        """Save the current session."""
        self.session_manager.save_session()

    def display_session_status(self) -> None:
        """Display current session status."""
        context_dict = self.session_manager.get_context_dict()
        self.interaction.display_session_status(context_dict)

    def clear_session(self) -> None:
        """Clear the current session."""
        self.session_manager.clear_session()
        self.tool_orchestrator.clear_cache()
        self.plan_executor.current_plan = None
        self.interaction.display_success("Session cleared")

    # Tool Execution
    def execute_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        show_result: bool = True,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Execute a single tool."""
        try:
            result = self.tool_orchestrator.execute_tool(
                tool_name, args, use_cache=use_cache
            )

            if show_result:
                self.interaction.display_tool_result(tool_name, result)

            # Update session state with results
            self._update_session_from_result(tool_name, result)
            self.session_manager.save_session()

            return result
        except (ValidationError, SecurityError) as e:
            self.interaction.display_error(f"Tool execution failed: {e}")
            raise e
        except Exception as e:
            self.interaction.display_error(f"An unexpected error occurred: {e}")
            return {"status": "failure", "error": str(e)}

    async def execute_tools_parallel(
        self, tool_requests: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Execute multiple tools in parallel."""
        results = await self.tool_orchestrator.execute_tools_parallel(tool_requests)

        # Display results and update session
        for i, result in enumerate(results):
            tool_name = tool_requests[i].get("tool", "unknown")
            self.interaction.display_tool_result(tool_name, result)
            self._update_session_from_result(tool_name, result)

        self.session_manager.save_session()
        return results

    def _update_session_from_result(
        self, tool_name: str, result: dict[str, Any]
    ) -> None:
        """Update session state based on tool results."""
        if result.get("status") != "success":
            return

        data = result.get("findings", {})

        # Handle different tool types
        if tool_name == "nmap" and "hosts" in data:
            for host in data["hosts"]:
                for port in host.get("open_ports", []):
                    self.session_manager.add_open_port(
                        port["port"], port.get("service", ""), port.get("version", "")
                    )

        elif tool_name == "ffuf" and "findings" in data:
            base_url = data.get("target_url", "")
            for finding in data["findings"]:
                url = f"{base_url}/{finding.get('path', '')}"
                self.session_manager.add_web_finding(url, "directory", finding)

        elif tool_name == "nikto" and "vulnerabilities" in data:
            url = data.get("target_url", "")
            self.session_manager.add_web_finding(
                url, "vulnerabilities", data["vulnerabilities"]
            )

    # Plan Management
    def create_plan(
        self, name: str, description: str, steps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Create a new reconnaissance plan."""
        plan = self.plan_executor.create_plan(name, description, steps)
        self.interaction.display_plan_summary(plan)

        # Save plan to session
        self.session_manager.current_plan = plan
        self.session_manager.save_session()

        return plan

    def execute_next_plan_step(self) -> bool:
        """Execute the next step in the current plan."""
        try:
            result = self.plan_executor.execute_next_step()
            if result:
                self.session_manager.save_session()
                return True
            return False
        except Exception as e:
            self.interaction.display_error(f"Plan execution failed: {e}")
            return False

    def get_plan_status(self) -> Optional[dict[str, Any]]:
        """Get current plan status."""
        return self.plan_executor.get_plan_status()

    # Interactive Sessions
    def start_interactive_session(self) -> None:
        """Start an interactive AI-guided reconnaissance session."""
        # Display ASCII banner and pro tips
        self.interaction.display_ascii_banner()

        # Get target for session
        target = self.get_target()

        # If no target is set, ask for one
        if not target:
            self.interaction.display_info("No target set. Let's get started!")
            target_input = self.interaction.prompt_input(
                "[cyan]Enter target IP address or hostname:[/cyan] "
            )

            if target_input.strip():
                self.set_target(target_input.strip())
                target = self.get_target()
            else:
                self.interaction.display_info(
                    "You can set a target later using the 'target' command."
                )

        # Display welcome with target
        self.interaction.display_welcome(target)

        # Display dry_run mode notice if enabled
        if self.dry_run:
            self.interaction.display_warning(
                "🔍 DRY RUN MODE ENABLED: Commands will be displayed but NOT executed. "
                "This is perfect for learning what tools would be run!"
            )

        # Display session status
        self.display_session_status()

        # Display a random pro tip
        import random

        pro_tips = [
            "Use Nmap with -sV to detect service versions for more targeted attacks!",
            "Check robots.txt and .git/ directories for hidden clues on web servers.",
            "Use ffuf with different wordlists for deeper directory brute-forcing.",
            "Look for usernames in HTML comments and error messages!",
            "Hydra is powerful, but always check for account lockout policies first.",
            "SMB shares can leak sensitive files—enumerate thoroughly!",
            "If you get stuck, ask: 'What else can we do?' or try a different tool!",
            "Nikto can reveal web server misconfigurations and vulnerabilities quickly.",
            "Use Expert Mode for less hand-holding and faster ops!",
        ]
        self.interaction.display_pro_tip(random.choice(pro_tips))

        self.interaction.display_info(
            "Type 'exit' or 'quit' to end recon and return to CLI."
        )

        # Initialize chat history properly
        if not self.session_manager.chat_history:
            # Add dry_run notice to system prompt if enabled
            dry_run_notice = (
                """
**DRY RUN MODE ACTIVE**: The user has enabled dry-run mode. In this mode:
- Tool commands will be displayed but NOT executed
- You should still propose tools normally using function calls
- The user will see the exact commands that would be run
- This is an excellent learning mode for understanding tool syntax
- Acknowledge this mode when suggesting tools by mentioning commands will be shown but not run

"""
                if self.dry_run
                else ""
            )

            # Use the full system prompt from the original agent
            system_prompt = (
                dry_run_notice
                + """You are Alien Recon, an AI assistant from Alien37.com. Your role is to be a helpful,
knowledgeable, and patient guide for users, especially beginners, who are working on
Capture The Flag (CTF) challenges. Your primary focus is on reconnaissance and initial
analysis to help them find their first flags or footholds.

Your primary directive is to assist ONLY with ethical hacking tasks for which the
user has explicit permission (like CTF platforms). **Assume user-provided targets
(IPs/domains) fall within the authorized scope of the CTF simulation after an
initial ethics reminder.** Do not repeatedly ask for permission confirmation
unless the user's request seems explicitly outside standard CTF boundaries.

Speak in a clear, encouraging, and direct tone, like an experienced cybersecurity
mentor or a helpful teammate. Explain cybersecurity concepts and the purpose of
tools and steps in a simple, understandable way. Avoid overly technical jargon
where possible, or explain it if necessary.

Your goal is to help the user understand reconnaissance, scanning, vulnerability
analysis, and potential exploitation paths, often following typical CTF workflows.
Be conversational and interactive, but also **concise and directive when guiding
the next step.** Explain *why* a step is taken briefly.

**WHEN you determine a specific scan or action is the logical next step based on the current context and findings, you MUST use the available 'tools' (function calls) to propose this action.**

**EDUCATIONAL PARAMETER EXPLANATIONS:**
When proposing tool functions, always provide brief educational explanations for non-default parameters:
- Explain WHY you're choosing specific scan types, ports, or wordlists
- Mention the trade-offs (e.g., "Using T4 timing for faster scans, but T3 would be more stealthy")
- Connect parameter choices to CTF/real-world scenarios

**IMPORTANT - Parallel Execution Optimization:**
- When multiple similar scans make sense, propose them ALL AT ONCE in a single response.
- The user's system supports parallel execution, so proposing multiple tools improves efficiency.
- Always explain that these tools can run simultaneously for faster results."""
            )
            self.session_manager.chat_history = [
                {"role": "system", "content": system_prompt}
            ]

            # If target is set, automatically suggest initial nmap scan
            if target:
                initial_user_msg = (
                    f"Initiate reconnaissance for primary target coordinates: {target}. "
                    "For the first step, please propose an initial Nmap scan using the `nmap_scan` tool. "
                    "A good initial scan for CTFs would be a SYN scan on the top 1000 TCP ports. "
                    "Use parameters like: "
                    '`target` should be the target IP, `scan_type="SYN"`, `ports="1-1000"`. '
                    "The skip_host_discovery parameter is already true by default which handles -Pn. "
                    "Only suggest service/version detection or other scans after these initial open ports are found. "
                    "Remember to propose this as a tool call."
                )
                self.session_manager.chat_history.append(
                    {"role": "user", "content": initial_user_msg}
                )

                # Get initial AI response with tool proposal
                ai_message = self._get_ai_response()
                if ai_message:
                    self._process_ai_message(ai_message)
        else:
            # Check if we need to restore pending tool calls
            self._check_and_handle_pending_messages()

        while True:
            try:
                user_input = self.interaction.prompt_input("\n[cyan]You:[/cyan]")

                if user_input.lower() in ["exit", "quit", "q"]:
                    break

                self.handle_user_input(user_input)

            except KeyboardInterrupt:
                self.interaction.display_info("Session interrupted by user")
                break
            except Exception as e:
                self.interaction.display_error(f"Unexpected error: {e}")
                logger.error(f"Interactive session error: {e}", exc_info=True)

    def handle_user_input(self, user_input: str) -> None:
        """Handle user input and get AI response."""
        # Check for flag capture celebration
        from .flag_celebrator import FlagCelebrator

        flag_found = FlagCelebrator.check_for_flag(user_input)
        if flag_found:
            FlagCelebrator.celebrate(flag_found)

        # Add user message to history
        self.session_manager.chat_history.append(
            {"role": "user", "content": user_input}
        )

        # Get AI response
        try:
            ai_message = self._get_ai_response()
            if ai_message:
                self._process_ai_message(ai_message)
        except Exception as e:
            self.interaction.display_error(f"AI response failed: {e}")
            logger.error(f"AI response error: {e}")

    def _get_ai_response(self) -> Optional[ChatCompletionMessage]:
        """Get response from AI agent."""
        try:
            # Build context
            context = self._build_context_for_ai()

            # Build the system prompt
            if self.mcp_agent and hasattr(self.mcp_agent, "_system_prompt"):
                # Use the dynamically built prompt from MCP agent
                base_prompt = self.mcp_agent._system_prompt
            else:
                # Fallback to static prompt
                from .agent import AGENT_SYSTEM_PROMPT

                base_prompt = AGENT_SYSTEM_PROMPT

            # Append context to system prompt
            full_system_prompt = f"{base_prompt}\n\nCurrent Context:\n{context}"

            # Get response using the existing OpenAI client
            # This preserves the existing flow where the MCP adapter handles tool calls
            from .agent import get_llm_response

            response = get_llm_response(
                self.openai_client,
                self.session_manager.chat_history,
                full_system_prompt,
            )

            return response if response else None
        except Exception as e:
            logger.error(f"Failed to get AI response: {e}")
            return None

    def _build_context_for_ai(self) -> str:
        """Build context string for AI."""
        # Use the comprehensive context summary from SessionManager
        return self.session_manager.get_context_summary()

    def _process_ai_message(self, ai_message: ChatCompletionMessage) -> None:
        """Process AI message using MCP adapter."""
        if not self.mcp_adapter:
            logger.error("MCP adapter not initialized")
            self.interaction.display_error("MCP adapter not initialized")
            return

        # Use MCP adapter to process the message
        try:
            # MCP adapter now has synchronous interface
            handled = self.mcp_adapter.process_ai_message(ai_message)

            if handled:
                # MCP handled the tool call, get next response
                self._get_next_ai_response()
        except Exception as e:
            logger.error(f"MCP processing failed: {e}")
            self.interaction.display_error(f"MCP processing failed: {e}")

    # Removed - no longer needed in MCP mode

    # Quick Recon
    def execute_quick_recon(self) -> None:
        """Execute a quick reconnaissance sequence."""
        target = self.get_target()
        if not target:
            self.interaction.display_error("No target set. Use set_target() first.")
            return

        # Create a quick recon plan
        steps = [
            {
                "tool": "nmap",
                "args": {"target": target, "scan_type": "quick"},
                "description": "Quick port scan",
            },
            {
                "tool": "nmap",
                "args": {"target": target, "scan_type": "service"},
                "description": "Service detection on open ports",
                "conditions": {"if_previous_success": True},
            },
        ]

        self.create_plan("Quick Recon", "Automated quick reconnaissance", steps)

        # Execute all steps
        while (
            self.plan_executor.current_plan
            and self.plan_executor.current_plan["status"] == "pending"
        ):
            if not self.execute_next_plan_step():
                break

    # CTF Context
    def set_ctf_context(self, metadata: dict[str, Any], box_identifier: str) -> None:
        """Set CTF context for the session."""
        self.session_manager.set_ctf_context(metadata, box_identifier)
        self.session_manager.save_session()
        self.interaction.display_success(f"CTF context set for: {box_identifier}")

    # Utility Methods
    def get_available_tools(self) -> list[str]:
        """Get list of available tools."""
        return self.tool_orchestrator.get_available_tools()

    def set_novice_mode(self, novice: bool) -> None:
        """Set novice mode for detailed explanations."""
        self.is_novice_mode = novice
        logger.info(f"Novice mode set to: {novice}")

    # Removed - no longer needed in MCP mode

    def continue_session(self) -> None:
        """Continue a previous session with context."""
        # Check if we have a valid session
        if not self.session_manager.chat_history:
            self.interaction.display_info("No previous session found")
            self.start_interactive_session()
            return

        # Display session context
        self.interaction.display_info("Resuming previous session...")
        context_summary = self.session_manager.get_context_summary()
        self.interaction.display_info(context_summary)

        # Check for pending actions
        if self.session_manager.current_plan:
            plan = self.session_manager.current_plan
            self.interaction.display_info(
                f"Active plan: {plan['plan_name']} "
                f"(Step {plan['current_step'] + 1}/{len(plan['steps'])})"
            )

            if self.interaction.prompt_confirmation(
                "Continue with the active plan?", default=True
            ):
                while self.execute_next_plan_step():
                    pass

        # Continue interactive session
        self.start_interactive_session()

    def _check_and_handle_pending_messages(self) -> None:
        """Check chat history for pending responses or tool calls."""
        if not self.session_manager.chat_history:
            return

        # Check if last message needs a response
        last_msg = self.session_manager.chat_history[-1]

        # If last message was from user or tool, get AI response
        if last_msg.get("role") in ["user", "tool"]:
            self.interaction.display_info("Getting AI response for previous message...")
            self._get_next_ai_response()

    def _get_next_ai_response(self) -> None:
        """Get the next AI response and process it."""
        try:
            ai_message = self._get_ai_response()
            if ai_message:
                self._process_ai_message(ai_message)
        except Exception as e:
            self.interaction.display_error(f"Failed to get AI response: {e}")
            logger.error(f"AI response error: {e}", exc_info=True)
