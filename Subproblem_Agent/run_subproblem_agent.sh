#!/bin/bash
# Script to run Subproblem Agent

echo "=========================================="
echo "Subproblem Agent - Setup and Run"
echo "=========================================="

# Navigate to Subproblem_Agent directory
cd "$(dirname "$0")" || exit 1

# Check if GROQ_API_KEY is set
if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ Error: GROQ_API_KEY environment variable is not set"
    echo "Please set it using: export GROQ_API_KEY='your-api-key'"
    exit 1
fi

echo "✓ GROQ_API_KEY is set"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    exit 1
fi

echo "✓ Python3 is available"

# Install dependencies if needed
echo ""
echo "Checking dependencies..."
if ! python3 -c "import groq" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
else
    echo "✓ Dependencies are installed"
fi

# Run the example script
echo ""
echo "Running Subproblem Agent..."
echo "=========================================="
python3 example_usage.py

