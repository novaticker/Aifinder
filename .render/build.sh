#!/usr/bin/env bash
set -e

echo "📦 Installing Python 3.10..."
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3.10-dev

echo "🔧 Setting up virtualenv with Python 3.10..."
python3.10 -m venv venv
source venv/bin/activate

echo "⬆️ Upgrading pip, setuptools..."
pip install --upgrade pip setuptools wheel

echo "📄 Installing requirements..."
pip install -r requirements.txt --no-build-isolation

echo "✅ Done"
