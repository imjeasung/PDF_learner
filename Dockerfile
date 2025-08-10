# Koyeb 배포용 Dockerfile
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (PDF 처리 및 컴파일용)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Python 모듈 경로 설정
ENV PYTHONPATH=/app:/app/backend

# 필요한 디렉토리 생성
RUN mkdir -p uploads data/extracted data/summaries data/vector_db static backend/ai_providers

# 권한 설정 (데이터 디렉토리들)
RUN chmod -R 755 uploads data static

# 포트 노출 (Koyeb은 8000 포트 사용)
EXPOSE 8000

# 헬스체크 추가 (Python requests 사용)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# uvicorn으로 FastAPI 앱 실행 (더 안정적인 설정)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "65"]