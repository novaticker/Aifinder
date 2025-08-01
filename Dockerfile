# 📦 Python 3.10 기반 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# pip 최신화 및 필수 패키지 설치
RUN pip install --upgrade pip setuptools wheel

# requirements 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 소스 복사
COPY . .

# 포트 설정 (Render가 환경변수로 PORT 넘김)
ENV PORT=10000

# 🌍 실행 명령 (gunicorn으로 Flask 실행)
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:$PORT", "--timeout", "120"]
