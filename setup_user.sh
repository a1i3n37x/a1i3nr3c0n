#!/bin/bash
set -e

echo "=== AlienRecon User Setup Script ==="
echo "This script will complete the AlienRecon setup for your user"
echo ""

# Add Poetry to PATH if needed
export PATH="$HOME/.local/bin:$PATH"

# Verify Poetry installation
echo "[1/5] Verifying Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Please run the system setup script first:"
    echo "  sudo ~/setup_alienrecon_fixed.sh"
    exit 1
fi

poetry --version

# Install project dependencies
echo "[2/5] Installing project dependencies with Poetry..."
cd /home/a1i3n37x/Documents/github/dev/a1i3nr3c0n
poetry install

# Activate virtual environment
echo "[3/5] Setting up virtual environment..."
poetry shell --no-interaction || true

# Install pre-commit hooks
echo "[4/5] Installing pre-commit hooks..."
poetry run pre-commit install

# Check if .env file exists and has API key
echo "[5/5] Checking environment configuration..."
if [ -f .env ]; then
    if grep -q "OPENAI_API_KEY=your-api-key-here" .env; then
        echo ""
        echo "⚠️  WARNING: You need to update your OpenAI API key in .env file"
        echo "Edit .env and replace 'your-api-key-here' with your actual API key"
    else
        echo "✓ .env file exists with API key configured"
    fi
else
    echo "Creating .env file..."
    echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo "⚠️  WARNING: You need to update your OpenAI API key in .env file"
fi

echo ""
echo "=== User setup complete! ==="
echo ""
echo "Next steps:"
echo "1. Update your OpenAI API key in .env file (if not already done)"
echo "2. Run: poetry shell (to activate the virtual environment)"
echo "3. Run: alienrecon doctor (to verify installation)"
echo "4. Start using AlienRecon!"
echo ""
echo "Example commands:"
echo "  alienrecon recon --target <IP>"
echo "  alienrecon quick-recon --target <IP>"
echo "  alienrecon manual nmap --target <IP>"