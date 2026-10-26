#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3 -m venv .build-venv
.build-venv/bin/python -m pip install -r build-requirements.txt
.build-venv/bin/python build_desktop.py
