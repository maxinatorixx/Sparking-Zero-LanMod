#!/usr/bin/env bash
set -euo pipefail
launcher_folder="$(cd -- "$(dirname -- "$0")" && pwd)"
if [[ -x "$launcher_folder/../dist/desktop/SzeroLAN-Linux" ]]; then
    exec "$launcher_folder/../dist/desktop/SzeroLAN-Linux"
fi
exec python3 "$launcher_folder/desktop.py"
