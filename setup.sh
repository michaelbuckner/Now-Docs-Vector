#!/bin/bash
# ServiceNow Documentation Vectorizer - Setup Script

echo "=========================================="
echo "ServiceNow Documentation Vectorizer Setup"
echo "=========================================="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi

echo "✅ Python $python_version detected"
echo

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "✅ Dependencies installed"
echo

# Run environment setup
echo "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    python3 setup_env.py
else
    echo ".env file already exists. Run 'python setup_env.py' to reconfigure."
fi

echo
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Verify setup: python test_setup.py"
echo "3. Index documentation: python index_docs.py"
echo "4. Test queries: python query_docs.py --interactive"
echo "5. Start MCP server: python mcp_server.py"
echo
