#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Auto-detect and switch to pickmyshow virtualenv if executed with system python
venv_python = Path.home() / '.venvs' / 'pickmyshow' / 'bin' / 'python'
if venv_python.exists() and sys.executable != str(venv_python) and not os.environ.get('VIRTUAL_ENV'):
    import subprocess
    sys.exit(subprocess.call([str(venv_python)] + sys.argv))


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PickMyShow.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

