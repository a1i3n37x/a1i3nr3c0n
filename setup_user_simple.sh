#!/bin/bash

echo "=== AlienRecon User Setup (Simple) ==="
echo ""

# Ensure we're in the right directory
cd /home/a1i3n37x/Documents/github/dev/a1i3nr3c0n

# Add local bin to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# Check if Poetry is available
if ! command -v poetry &> /dev/null; then
    echo "ERROR: Poetry not found!"
    echo "Please ensure you ran the system setup as root first."
    echo "If Poetry was just installed, try: source ~/.bashrc"
    exit 1
fi

echo "✓ Poetry found: $(poetry --version)"

# Install dependencies
echo ""
echo "Installing project dependencies..."
poetry install

# Set up pre-commit hooks
echo ""
echo "Setting up pre-commit hooks..."
poetry run pre-commit install || echo "Pre-commit hooks setup skipped"

# Check .env file
echo ""
if [ -f .env ]; then
    if grep -q "OPENAI_API_KEY=sk-" .env; then
        echo "✓ OpenAI API key is configured in .env"
    else
        echo "⚠️  Please verify your OpenAI API key in .env file"
    fi
else
    echo "⚠️  No .env file found. Creating one..."
    echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo "Please edit .env and add your OpenAI API key"
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To start using AlienRecon:"
echo "1. Activate the virtual environment: poetry shell"
echo "2. Test the installation: alienrecon doctor"
echo "3. Start reconnaissance: alienrecon recon --target <IP>"
echo ""
echo "Quick test commands:"
echo "  alienrecon --help"
echo "  alienrecon status"
echo "  alienrecon manual nmap --help"