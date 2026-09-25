#!/bin/bash
# If the project's dedicated virtualenv exists, execute directly with it
if [ -f "$HOME/.venvs/pickmyshow/bin/python" ]; then
    unset PYTHONPATH
    exec "$HOME/.venvs/pickmyshow/bin/python" "$@"
fi

export PYTHONPATH=$(/usr/bin/python3 -c "
import glob
paths = []
for p in glob.glob('/home/dev-abxn/.cache/uv/archive-v0/*'):
    if 'aserrYl94CiM6Z-E' in p:
        continue
    so_files = glob.glob(p + '/**/*.so', recursive=True)
    if so_files:
        if any('314' in f for f in so_files):
            paths.append(p)
    else:
        paths.append(p)
print(':'.join(paths))
"):$PYTHONPATH
export VIRTUAL_ENV=sandbox

exec /usr/bin/python3 "$@"
