#!/usr/bin/env bash
set -e

echo "⬆️ Upgrading pip, setuptools..."
pip install --upgrade pip==23.2.1 setuptools==65.5.0 wheel==0.40.0

echo "📄 Installing requirements..."
pip install --no-use-pep517 --no-build-isolation -r requirements.txt

echo "✅ Build finished successfully!"
