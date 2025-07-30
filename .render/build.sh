#!/usr/bin/env bash

set -e

echo "🔧 Installing dependencies..."

# isolation 비활성화 + 빌드 도구 설치
export PIP_NO_BUILD_ISOLATION=1
pip install --upgrade pip setuptools wheel

# 프로젝트 의존성 설치
pip install -r requirements.txt

echo "✅ Build completed."
