#!/usr/bin/env bash
# Parrot Desktop Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -d "$DIR/.venv" ]; then
    source "$DIR/.venv/bin/activate"
fi

echo "🦜 Abrindo Parrot — Aplicação Desktop Nativa macOS..."
python3 "$DIR/main.py" "$@"
