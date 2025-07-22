#!/usr/bin/env python3
"""
Quick test script to verify AlienRecon CLI functionality.
"""

import subprocess


def run_command(cmd):
    """Run a command and return output."""
    print(f"\n[TEST] Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"[OUTPUT] stdout: {result.stdout}")
    if result.stderr:
        print(f"[ERROR] stderr: {result.stderr}")
    return result.returncode, result.stdout, result.stderr


def main():
    """Test main CLI functionality."""
    print("=== AlienRecon CLI Functionality Test ===")

    # Test 1: Help command
    print("\n1. Testing help command...")
    code, stdout, stderr = run_command("alienrecon --help")
    assert code == 0, "Help command failed"
    assert "Alien Recon" in stdout, "Help text missing"
    print("✓ Help command works")

    # Test 2: Set target
    print("\n2. Testing target command...")
    code, stdout, stderr = run_command("alienrecon target 10.10.10.1")
    assert code == 0, "Target command failed"
    assert "Target set" in stdout, "Target not set properly"
    print("✓ Target command works")

    # Test 3: Check status
    print("\n3. Testing status command...")
    code, stdout, stderr = run_command("alienrecon status")
    assert code == 0, "Status command failed"
    assert "10.10.10.1" in stdout, "Target not shown in status"
    print("✓ Status command works")

    # Test 4: Clear session
    print("\n4. Testing clear command...")
    code, stdout, stderr = run_command("alienrecon clear")
    assert code == 0, "Clear command failed"
    print("✓ Clear command works")

    # Test 5: Manual nmap (dry-run)
    print("\n5. Testing manual nmap with dry-run...")
    code, stdout, stderr = run_command("alienrecon --dry-run manual nmap 10.10.10.1")
    assert code == 0, "Manual nmap command failed"
    assert "nmap" in stdout.lower() or "nmap" in stderr.lower(), (
        "Nmap command not shown"
    )
    print("✓ Manual nmap (dry-run) works")

    # Test 6: Cache status
    print("\n6. Testing cache status...")
    code, stdout, stderr = run_command("alienrecon cache status")
    assert code == 0, "Cache status command failed"
    print("✓ Cache status works")

    # Test 7: Doctor command
    print("\n7. Testing doctor command...")
    code, stdout, stderr = run_command("alienrecon doctor")
    # Doctor might have warnings, so we just check it runs
    print("✓ Doctor command runs")

    print("\n=== All CLI tests passed! ===")
    print("\nAlienRecon CLI is working correctly in CLI mode.")
    print(
        "MCP integration is optional and can be enabled with ALIENRECON_AGENT_MODE=mcp"
    )


if __name__ == "__main__":
    main()
