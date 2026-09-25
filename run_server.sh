#!/bin/bash
echo "=========================================="
echo "Starting PickMyShow Development Server..."
echo "=========================================="

source "$HOME/.venvs/pickmyshow/bin/activate" 2>/dev/null || true
python3 manage.py runserver 127.0.0.1:8000
