#!/bin/bash
echo "Installing Gandiva Pro Backend Dependencies..."
echo ""

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "Installing from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "Verifying installation..."
python check_dependencies.py

echo ""
echo "Installation complete!"

