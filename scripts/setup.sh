#!/bin/sh

set -eu

python3 -m venv .venv

. .venv/bin/activate

pip install -r requirements.txt

mkdir -p storage/uploads
mkdir -p models/weights
mkdir -p training/data
mkdir -p training/output

echo "Lumen setup complete."
