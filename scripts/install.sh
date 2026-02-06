#!/bin/bash
# Paperstack installation script

set -e

echo "Installing Paperstack..."

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Project directory: $PROJECT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

# Activate virtual environment
source "$PROJECT_DIR/.venv/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install package in development mode
echo "Installing Paperstack..."
pip install -e "$PROJECT_DIR"

# Initialize database
echo "Initializing database..."
paperstack init

echo ""
echo "Installation complete!"
echo ""
echo "Paperstack has been installed. You can now use it by:"
echo "  1. Activating the virtual environment: source $PROJECT_DIR/.venv/bin/activate"
echo "  2. Running: paperstack --help"
echo ""
echo "Or add this to your shell profile for global access:"
echo "  alias paperstack='$PROJECT_DIR/.venv/bin/paperstack'"
echo ""
echo "Quick start:"
echo "  paperstack add url 'https://arxiv.org/abs/2301.07041'"
echo "  paperstack reading list"
echo "  paperstack shell"
