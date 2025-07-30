#!/usr/bin/env bash
set -e

echo "⬆️ Upgrading pip, setuptools, wheel..."
pip install --upgrade pip==23.2.1 setuptools==65.5.0 wheel==0.40.0

echo "📄 Installing requirements..."
pip install --no-build-isolation --no-use-pep517 -r requirements.txt

echo "✅ Build successful."
