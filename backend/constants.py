# 프로젝트 상수 정의 모듈
# 하드코딩된 값들을 중앙에서 관리합니다.

from typing import List, Dict

# ===== 파일 처리 관련 상수 =====

# 파일 크기 제한
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# 허용되는 파일 타입
ALLOWED_MIME_TYPES = ['application/pdf']
ALLOWED_FILE_EXTENSIONS = ['.pdf']

# 파일 검증 상수
PDF_MAGIC_BYTES = b'%PDF-'  # PDF 파일 시작 바이트

# ===== AI 처리 관련 상수 =====

# OpenAI 기본 설정
DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo"
DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE = 0.7

# 텍스트 처리 설정
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MIN_CHUNK_LENGTH = 50  # 너무 짧은 텍스트 제외 기준

# 임베딩 처리 설정
DEFAULT_EMBEDDING_BATCH_SIZE = 50
DEFAULT_EMBEDDING_DIMENSION = 1536  # ada-002 기본 차원

# 페이지 텍스트 분할 설정
PAGE_CHUNK_SIZE = 500
TEXT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

# ===== 데이터베이스 관련 상수 =====

# 기본 데이터베이스 URL
DEFAULT_DATABASE_URL = "sqlite:///./pdf_learner.db"

# 문서 처리 상태
PROCESSING_STATUS = {
    'UPLOADED': 'uploaded',
    'PROCESSING': 'processing', 
    'COMPLETED': 'completed',
    'FAILED': 'failed'
}

# 쿼리 제한
DEFAULT_DOCUMENT_LIMIT = 100
MAX_SEARCH_RESULTS = 10

# ===== 커리큘럼 생성 관련 상수 =====

# 기본 섹션 이름들
DEFAULT_SECTION_NAMES = [
    "도입",
    "주요 내용", 
    "심화 학습",
    "결론",
    "참고사항"
]

# 섹션 생성 범위
MIN_SECTIONS = 3
MAX_SECTIONS = 5
DEFAULT_SECTIONS_COUNT = 4

# AI 프롬프트 제한
MAX_PROMPT_LENGTH = 3000
MAX_SAMPLE_TEXT_LENGTH = 2000

# ===== 벡터 검색 관련 상수 =====

# 검색 기본값
DEFAULT_TOP_K = 3
MAX_TOP_K = 10
MIN_SIMILARITY_THRESHOLD = 0.5

# ChromaDB 설정
CHROMA_COLLECTION_PREFIX = "doc_"
MAX_COLLECTION_NAME_LENGTH = 100

# ===== 웹 서버 관련 상수 =====

# 서버 기본 설정
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# CORS 기본 설정
DEFAULT_CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

# 정적 파일 경로
STATIC_PATHS = {
    'CSS': 'frontend/css',
    'JS': 'frontend',
    'UPLOADS': 'uploads'
}

# ===== HTTP 응답 관련 상수 =====

# 성공 메시지
SUCCESS_MESSAGES = {
    'UPLOAD': '파일이 성공적으로 업로드되었습니다.',
    'DELETE': '파일이 삭제되었습니다.',
    'PROCESS': 'AI 분석이 완료되었습니다.',
    'DOWNLOAD': '파일 다운로드가 시작되었습니다.'
}

# 에러 메시지
ERROR_MESSAGES = {
    'FILE_NOT_FOUND': '파일을 찾을 수 없습니다.',
    'INVALID_FILE_TYPE': 'PDF 파일만 업로드 가능합니다.',
    'FILE_TOO_LARGE': f'파일 크기는 {MAX_FILE_SIZE_MB}MB를 초과할 수 없습니다.',
    'AI_NOT_INITIALIZED': 'AI 서비스가 초기화되지 않았습니다.',
    'OPENAI_KEY_MISSING': 'OPENAI_API_KEY가 설정되지 않았습니다.',
    'PROCESSING_FAILED': 'AI 처리 중 오류가 발생했습니다.',
    'DATABASE_ERROR': '데이터베이스 오류가 발생했습니다.'
}

# HTTP 상태 코드
HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'NOT_FOUND': 404,
    'INTERNAL_ERROR': 500,
    'SERVICE_UNAVAILABLE': 503
}

# ===== 로깅 관련 상수 =====

# 로그 레벨
LOG_LEVELS = {
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'ERROR': 'ERROR',
    'CRITICAL': 'CRITICAL'
}

# 로그 포맷
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# ===== 보안 관련 상수 =====

# 파일명 검증 패턴
SAFE_FILENAME_PATTERN = r'^[a-zA-Z0-9가-힣\s\-_\.()]+$'
MAX_FILENAME_LENGTH = 255

# 허용되지 않는 파일명 패턴
FORBIDDEN_FILENAME_PATTERNS = [
    r'\.\.', # 상위 디렉토리 접근
    r'^\.', # 숨김 파일
    r'[<>:"/\\|?*]', # 특수 문자
]

# ===== 성능 관련 상수 =====

# 타임아웃 설정 (초)
TIMEOUTS = {
    'OPENAI_REQUEST': 60,
    'FILE_UPLOAD': 300,
    'DATABASE_QUERY': 30,
    'HEALTH_CHECK': 10
}

# 메모리 제한
MAX_MEMORY_MB = 512
MAX_CONCURRENT_UPLOADS = 3

# ===== UI 관련 상수 =====

# 메시지 타입
MESSAGE_TYPES = {
    'SUCCESS': 'success',
    'ERROR': 'error', 
    'WARNING': 'warning',
    'INFO': 'info'
}

# 아이콘 매핑
MESSAGE_ICONS = {
    'success': 'check-circle',
    'error': 'exclamation-circle',
    'warning': 'exclamation-triangle',
    'info': 'info-circle'
}

# 색상 코드
MESSAGE_COLORS = {
    'success': 'linear-gradient(45deg, #2ecc71, #27ae60)',
    'error': 'linear-gradient(45deg, #e74c3c, #c0392b)',
    'warning': 'linear-gradient(45deg, #f39c12, #e67e22)',
    'info': 'linear-gradient(45deg, #3498db, #2980b9)'
}

# ===== 개발/배포 환경 관련 상수 =====

# 환경 타입
ENVIRONMENTS = {
    'DEVELOPMENT': 'development',
    'PRODUCTION': 'production',
    'TESTING': 'testing'
}

# Koyeb 관련 상수
KOYEB_ENV_VARS = [
    'KOYEB_PUBLIC_DOMAIN',
    'KOYEB_DEPLOYMENT_ID',
    'KOYEB_SERVICE_NAME'
]

# ===== 버전 정보 =====
APP_VERSION = "1.0.0"
API_VERSION = "v1"

# ===== 헬퍼 함수들 =====

def get_allowed_extensions() -> List[str]:
    """허용되는 파일 확장자 목록 반환"""
    return ALLOWED_FILE_EXTENSIONS.copy()

def get_processing_statuses() -> List[str]:
    """모든 처리 상태 목록 반환"""
    return list(PROCESSING_STATUS.values())

def is_valid_processing_status(status: str) -> bool:
    """유효한 처리 상태인지 확인"""
    return status in PROCESSING_STATUS.values()

def get_error_message(key: str) -> str:
    """에러 메시지 키로 메시지 반환"""
    return ERROR_MESSAGES.get(key, "알 수 없는 오류가 발생했습니다.")

def get_success_message(key: str) -> str:
    """성공 메시지 키로 메시지 반환"""
    return SUCCESS_MESSAGES.get(key, "작업이 완료되었습니다.")

# 모듈 테스트용
if __name__ == "__main__":
    print("📋 Constants 모듈 테스트")
    print("=" * 50)
    
    print(f"파일 크기 제한: {MAX_FILE_SIZE_MB}MB")
    print(f"허용 파일 타입: {ALLOWED_MIME_TYPES}")
    print(f"기본 섹션: {DEFAULT_SECTION_NAMES}")
    print(f"처리 상태: {list(PROCESSING_STATUS.values())}")
    print(f"앱 버전: {APP_VERSION}")
    
    print("\n🎉 Constants 모듈 테스트 완료!")