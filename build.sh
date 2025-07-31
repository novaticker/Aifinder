#!/bin/bash
set -e

echo "🔧 Updating pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

echo "📦 Installing requirements with no build isolation..."
pip install --no-build-isolation -r requirements.txt

echo "✅ Build finished successfully!"
