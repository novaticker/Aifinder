#!/usr/bin/env bash
set -e

echo "📦 Installing system packages..."
apt-get update && apt-get install -y python3.10 python3.10-venv python3.10-dev

echo "🐍 Creating virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

echo "⬆️ Upgrading pip & setuptools..."
pip install --upgrade pip setuptools wheel

echo "📄 Installing Python dependencies..."
pip install --no-build-isolation --no-use-pep517 -r requirements.txt

echo "✅ Build complete."
