#!/usr/bin/env bash
# Parrot Startup Script
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Configurando ambiente Python com uv..."
    uv venv --python 3.12 .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "Iniciando o Parrot..."
python3 main.py "$@"
