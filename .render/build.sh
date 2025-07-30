#!/usr/bin/env bash
set -e

echo "🔧 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Upgrading pip & setuptools..."
pip install --upgrade pip setuptools wheel

echo "📄 Installing requirements..."
pip install -r requirements.txt --no-build-isolation

echo "✅ Build completed."
