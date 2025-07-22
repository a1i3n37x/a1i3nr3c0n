#!/bin/bash
# Script to test MCP integration

echo "=== AlienRecon MCP Integration Test ==="
echo

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set"
    echo "Please set it: export OPENAI_API_KEY=your-key"
    exit 1
fi

# Start the test MCP server in background
echo "Starting test MCP server..."
python test_mcp_server.py &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Check if server is running
if ! curl -s http://localhost:50051/health > /dev/null; then
    echo "❌ Failed to start MCP server"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "✓ MCP server is running"
echo

# Run the end-to-end test
echo "Running MCP integration test..."
export ALIENRECON_AGENT_MODE=mcp
python test_mcp_e2e.py

# Capture exit code
TEST_RESULT=$?

# Stop the server
echo
echo "Stopping MCP server..."
kill $SERVER_PID 2>/dev/null

# Exit with test result
exit $TEST_RESULT
