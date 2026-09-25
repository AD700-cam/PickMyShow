#!/bin/bash
echo "=========================================="
echo "Starting PickMyShow Celery Worker..."
echo "=========================================="

source "$HOME/.venvs/pickmyshow/bin/activate" 2>/dev/null || true
celery -A PickMyShow worker -l info
