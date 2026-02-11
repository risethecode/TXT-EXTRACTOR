#!/bin/bash

echo "Container Started..."
echo "Starting Bot..."

cd /EXTRACTOR || exit

python -m Extractor
