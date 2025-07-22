#!/usr/bin/env python3
"""
Comprehensive test runner for AlienRecon MCP integration.

This script runs all tests and provides a detailed report on:
- What's working
- What's broken
- Coverage statistics
- Performance metrics
"""

import subprocess
import time
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text):
    """Print a section header."""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{text:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_status(component, status, details=""):
    """Print component status."""
    if status == "PASS":
        symbol = f"{GREEN}✓{RESET}"
        status_color = GREEN
    elif status == "FAIL":
        symbol = f"{RED}✗{RESET}"
        status_color = RED
    elif status == "WARN":
        symbol = f"{YELLOW}⚠{RESET}"
        status_color = YELLOW
    else:
        symbol = "?"
        status_color = RESET

    print(f"{symbol} {component:<40} {status_color}{status:>10}{RESET} {details}")


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{YELLOW}Running: {description}{RESET}")
    print(f"Command: {' '.join(cmd)}")

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    if result.returncode == 0:
        print(f"{GREEN}✓ Success ({elapsed:.2f}s){RESET}")
        return True, result.stdout, elapsed
    else:
        print(f"{RED}✗ Failed ({elapsed:.2f}s){RESET}")
        if result.stderr:
            print(f"{RED}Error: {result.stderr}{RESET}")
        return False, result.stdout + result.stderr, elapsed


def check_imports():
    """Check if all modules can be imported."""
    print_header("Import Checks")

    modules = [
        ("alienrecon.config", "Configuration module"),
        ("alienrecon.core.mcp_client", "MCP Client"),
        ("alienrecon.core.mcp_agent", "MCP Agent"),
        ("alienrecon.core.mcp_server_manager", "MCP Server Manager"),
        ("alienrecon.core.mcp_session_adapter", "MCP Session Adapter"),
        ("alienrecon.core.refactored_session_controller", "Session Controller"),
    ]

    all_pass = True
    for module, description in modules:
        try:
            __import__(module)
            print_status(description, "PASS", f"Module: {module}")
        except ImportError as e:
            print_status(description, "FAIL", str(e))
            all_pass = False

    return all_pass


def run_unit_tests():
    """Run unit tests."""
    print_header("Unit Tests")

    test_files = [
        "tests/unit/test_mcp_client.py",
        "tests/unit/test_mcp_server_manager.py",
    ]

    results = {}
    for test_file in test_files:
        if Path(test_file).exists():
            success, output, elapsed = run_command(
                ["python", "-m", "pytest", test_file, "-v"],
                f"Unit tests: {Path(test_file).name}",
            )
            results[test_file] = (success, elapsed)
        else:
            print(f"{YELLOW}⚠ Test file not found: {test_file}{RESET}")
            results[test_file] = (False, 0)

    return results


def run_integration_tests():
    """Run integration tests."""
    print_header("Integration Tests")

    test_file = "tests/integration/test_mcp_workflow.py"

    if Path(test_file).exists():
        success, output, elapsed = run_command(
            ["python", "-m", "pytest", test_file, "-v"], "Integration tests"
        )
        return success, elapsed
    else:
        print(f"{YELLOW}⚠ Test file not found: {test_file}{RESET}")
        return False, 0


def run_e2e_tests():
    """Run end-to-end tests."""
    print_header("End-to-End Tests")

    test_file = "tests/e2e/test_complete_workflow.py"

    if Path(test_file).exists():
        success, output, elapsed = run_command(
            ["python", "-m", "pytest", test_file, "-v"], "E2E tests"
        )
        return success, elapsed
    else:
        print(f"{YELLOW}⚠ Test file not found: {test_file}{RESET}")
        return False, 0


def check_coverage():
    """Run tests with coverage."""
    print_header("Coverage Analysis")

    success, output, elapsed = run_command(
        [
            "python",
            "-m",
            "pytest",
            "--cov=src/alienrecon",
            "--cov-report=term-missing",
            "--cov-report=html",
            "tests/",
        ],
        "Coverage analysis",
    )

    if success:
        # Extract coverage percentage from output
        for line in output.split("\n"):
            if "TOTAL" in line:
                print(f"\n{BOLD}Coverage Summary:{RESET} {line}")

    return success


def test_cli_commands():
    """Test CLI commands work."""
    print_header("CLI Command Tests")

    commands = [
        (["python", "-m", "alienrecon", "--help"], "Help command"),
        (["python", "-m", "alienrecon", "agent-mode"], "Agent mode check"),
        (["python", "-m", "alienrecon", "doctor"], "Doctor command"),
    ]

    results = {}
    for cmd, description in commands:
        success, output, elapsed = run_command(cmd, description)
        results[description] = success

    return results


def check_mcp_components():
    """Check MCP component functionality."""
    print_header("MCP Component Status")

    # Test basic instantiation
    test_script = """
import sys
sys.path.insert(0, "src")

# Test imports
try:
    from alienrecon.config import Config
    from alienrecon.core.mcp_client import MCPClient, MCPServer
    from alienrecon.core.mcp_server_manager import MCPServerManager
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test configuration
try:
    config = Config()
    # MCP mode is now the default
    print("✓ Configuration works")
except Exception as e:
    print(f"✗ Configuration failed: {e}")
    sys.exit(1)

# Test MCP client
try:
    client = MCPClient()
    server = MCPServer(
        name="test",
        url="http://localhost:50051",
        description="Test",
        tools=["test_tool"]
    )
    client.register_server(server)
    assert "test" in client.servers
    print("✓ MCP Client works")
except Exception as e:
    print(f"✗ MCP Client failed: {e}")
    sys.exit(1)

# Test server manager
try:
    manager = MCPServerManager()
    configs = manager.get_server_configs()
    print(f"✓ Server Manager works (found {len(configs)} server configs)")
except Exception as e:
    print(f"✗ Server Manager failed: {e}")
    sys.exit(1)

print("\\nAll MCP components functional!")
"""

    success, output, elapsed = run_command(
        ["python", "-c", test_script], "MCP component functionality"
    )

    if output:
        print(output)

    return success


def generate_report(results):
    """Generate final test report."""
    print_header("Test Summary Report")

    # Component status
    print(f"{BOLD}Component Status:{RESET}")
    print_status("Import checks", results["imports"])
    print_status("MCP components", results["mcp_components"])
    print_status(
        "CLI commands", "PASS" if all(results["cli_commands"].values()) else "FAIL"
    )

    # Test results
    print(f"\n{BOLD}Test Results:{RESET}")

    # Unit tests
    unit_pass = all(success for success, _ in results["unit_tests"].values())
    print_status(
        "Unit tests",
        "PASS" if unit_pass else "FAIL",
        f"{sum(1 for s, _ in results['unit_tests'].values() if s)}/{len(results['unit_tests'])} passed",
    )

    # Integration tests
    print_status(
        "Integration tests", "PASS" if results["integration_tests"][0] else "FAIL"
    )

    # E2E tests
    print_status("E2E tests", "PASS" if results["e2e_tests"][0] else "FAIL")

    # Coverage
    print_status("Coverage analysis", "PASS" if results["coverage"] else "FAIL")

    # Overall assessment
    print(f"\n{BOLD}Overall Assessment:{RESET}")

    all_pass = (
        results["imports"]
        and results["mcp_components"]
        and unit_pass
        and results["integration_tests"][0]
        and results["e2e_tests"][0]
    )

    if all_pass:
        print(
            f"{GREEN}{BOLD}✓ All tests passing! MCP integration is working correctly.{RESET}"
        )
    else:
        print(f"{RED}{BOLD}✗ Some tests failed. See details above.{RESET}")

    # Recommendations
    print(f"\n{BOLD}Recommendations:{RESET}")

    if not results["imports"]:
        print("- Fix import errors before proceeding")

    if not results["mcp_components"]:
        print("- Check MCP component implementations")

    if not unit_pass:
        print("- Fix failing unit tests")

    if not results["integration_tests"][0]:
        print("- Debug integration test failures")

    if not results["e2e_tests"][0]:
        print("- Investigate E2E workflow issues")

    if all_pass:
        print("- Ready for production testing!")
        print("- Consider adding more edge case tests")
        print("- Set up CI/CD pipeline")


def main():
    """Run all tests and generate report."""
    print(f"{BOLD}AlienRecon MCP Integration Test Suite{RESET}")
    print(f"Testing from: {Path.cwd()}")

    # Change to project root if needed
    if Path("src/alienrecon").exists():
        print("✓ Running from project root")
    else:
        print("✗ Not in project root, tests may fail")

    results = {}

    # Run all test categories
    results["imports"] = check_imports()
    results["mcp_components"] = check_mcp_components()
    results["cli_commands"] = test_cli_commands()
    results["unit_tests"] = run_unit_tests()
    results["integration_tests"] = run_integration_tests()
    results["e2e_tests"] = run_e2e_tests()
    results["coverage"] = check_coverage()

    # Generate report
    generate_report(results)


if __name__ == "__main__":
    main()
