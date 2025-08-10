# 프로젝트 유틸리티 함수 모듈
# 공통으로 사용되는 함수들을 중앙에서 관리합니다.

import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import mimetypes

from .constants import (
    MAX_FILE_SIZE_BYTES, ALLOWED_MIME_TYPES, ALLOWED_FILE_EXTENSIONS,
    PDF_MAGIC_BYTES, SAFE_FILENAME_PATTERN, MAX_FILENAME_LENGTH,
    FORBIDDEN_FILENAME_PATTERNS, ERROR_MESSAGES, SUCCESS_MESSAGES
)

# ===== 파일 관련 유틸리티 =====

def validate_file_basic(filename: str, file_size: int) -> Tuple[bool, str]:
    """
    기본 파일 검증 (확장자, 크기, 파일명)
    
    Args:
        filename: 파일명
        file_size: 파일 크기 (바이트)
        
    Returns:
        (검증 통과 여부, 오류 메시지)
    """
    # 파일명 검증
    if not filename:
        return False, "파일명이 없습니다."
    
    if len(filename) > MAX_FILENAME_LENGTH:
        return False, f"파일명이 너무 깁니다. ({MAX_FILENAME_LENGTH}자 이하)"
    
    # 안전하지 않은 파일명 패턴 검사
    for pattern in FORBIDDEN_FILENAME_PATTERNS:
        if re.search(pattern, filename):
            return False, "허용되지 않는 문자가 포함된 파일명입니다."
    
    # 확장자 검증
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_FILE_EXTENSIONS:
        return False, ERROR_MESSAGES['INVALID_FILE_TYPE']
    
    # 파일 크기 검증
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, ERROR_MESSAGES['FILE_TOO_LARGE']
    
    if file_size == 0:
        return False, "빈 파일은 업로드할 수 없습니다."
    
    return True, ""

def validate_pdf_content(file_content: bytes) -> Tuple[bool, str]:
    """
    PDF 파일 내용 검증 (매직 바이트, 구조)
    
    Args:
        file_content: 파일 바이트 내용
        
    Returns:
        (검증 통과 여부, 오류 메시지)
    """
    if not file_content:
        return False, "파일 내용이 없습니다."
    
    # PDF 매직 바이트 검증
    if not file_content.startswith(PDF_MAGIC_BYTES):
        return False, "유효한 PDF 파일이 아닙니다."
    
    # PDF 구조 기본 검증 (%%EOF 확인)
    if b'%%EOF' not in file_content[-1024:]:  # 마지막 1KB에서 EOF 확인
        return False, "손상된 PDF 파일일 수 있습니다."
    
    return True, ""

def get_mime_type(file_content: bytes, filename: str) -> str:
    """
    파일 내용과 확장자로 MIME 타입 추정
    
    Args:
        file_content: 파일 바이트 내용
        filename: 파일명
        
    Returns:
        MIME 타입 문자열
    """
    # 확장자 기반 MIME 타입
    mime_type, _ = mimetypes.guess_type(filename)
    
    # PDF 매직 바이트로 검증
    if file_content.startswith(PDF_MAGIC_BYTES):
        return 'application/pdf'
    
    return mime_type or 'application/octet-stream'

def sanitize_filename(filename: str) -> str:
    """
    파일명을 안전하게 정리
    
    Args:
        filename: 원본 파일명
        
    Returns:
        정리된 파일명
    """
    # 기본 정리
    clean_name = filename.strip()
    
    # 위험한 문자 제거
    for pattern in FORBIDDEN_FILENAME_PATTERNS:
        clean_name = re.sub(pattern, '_', clean_name)
    
    # 연속된 공백을 하나로
    clean_name = re.sub(r'\s+', ' ', clean_name)
    
    # 길이 제한
    if len(clean_name) > MAX_FILENAME_LENGTH:
        name_part, ext = os.path.splitext(clean_name)
        max_name_len = MAX_FILENAME_LENGTH - len(ext)
        clean_name = name_part[:max_name_len] + ext
    
    return clean_name

def generate_safe_filename(original_filename: str, add_timestamp: bool = False) -> str:
    """
    안전한 파일명 생성
    
    Args:
        original_filename: 원본 파일명
        add_timestamp: 타임스탬프 추가 여부
        
    Returns:
        안전한 파일명
    """
    clean_name = sanitize_filename(original_filename)
    name_part, ext = os.path.splitext(clean_name)
    
    if add_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_part = f"{name_part}_{timestamp}"
    
    return f"{name_part}{ext}"

# ===== 경로 관련 유틸리티 =====

def ensure_directory(path: str) -> bool:
    """
    디렉토리가 존재하지 않으면 생성
    
    Args:
        path: 디렉토리 경로
        
    Returns:
        생성 성공 여부
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"❌ 디렉토리 생성 실패 {path}: {e}")
        return False

def get_safe_path(base_path: str, filename: str) -> str:
    """
    안전한 파일 경로 생성 (경로 조작 방지)
    
    Args:
        base_path: 기준 경로
        filename: 파일명
        
    Returns:
        안전한 전체 경로
    """
    # 파일명 정리
    safe_filename = sanitize_filename(filename)
    
    # 경로 조작 방지
    safe_path = os.path.join(base_path, safe_filename)
    safe_path = os.path.normpath(safe_path)
    
    # 기준 경로를 벗어나는지 확인
    if not safe_path.startswith(os.path.normpath(base_path)):
        raise ValueError("허용되지 않는 경로입니다.")
    
    return safe_path

def get_file_size_mb(file_size_bytes: int) -> float:
    """
    바이트를 MB로 변환
    
    Args:
        file_size_bytes: 바이트 크기
        
    Returns:
        MB 크기 (소수점 2자리)
    """
    return round(file_size_bytes / (1024 * 1024), 2)

# ===== 텍스트 처리 유틸리티 =====

def clean_text(text: str) -> str:
    """
    텍스트 정리 (공백, 개행 등)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        정리된 텍스트
    """
    if not text:
        return ""
    
    # 연속된 공백과 개행 정리
    clean = re.sub(r'\s+', ' ', text.strip())
    
    # 특수 유니코드 문자 정리
    clean = re.sub(r'[\u200b-\u200d\ufeff]', '', clean)
    
    return clean

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    텍스트 길이 제한
    
    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 생략 표시
        
    Returns:
        제한된 텍스트
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_filename_without_ext(filepath: str) -> str:
    """
    파일 경로에서 확장자 없는 파일명 추출
    
    Args:
        filepath: 파일 경로
        
    Returns:
        확장자 없는 파일명
    """
    return Path(filepath).stem

# ===== 해시 관련 유틸리티 =====

def generate_file_hash(file_content: bytes) -> str:
    """
    파일 내용의 MD5 해시 생성
    
    Args:
        file_content: 파일 바이트 내용
        
    Returns:
        MD5 해시 문자열
    """
    return hashlib.md5(file_content).hexdigest()

def generate_short_id(text: str, length: int = 8) -> str:
    """
    텍스트에서 짧은 ID 생성
    
    Args:
        text: 원본 텍스트
        length: ID 길이
        
    Returns:
        짧은 ID 문자열
    """
    hash_value = hashlib.md5(text.encode('utf-8')).hexdigest()
    return hash_value[:length]

# ===== 날짜/시간 유틸리티 =====

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    날짜시간 포맷팅
    
    Args:
        dt: datetime 객체
        format_str: 포맷 문자열
        
    Returns:
        포맷된 문자열
    """
    if not dt:
        return ""
    return dt.strftime(format_str)

def get_current_timestamp() -> str:
    """현재 타임스탬프 문자열 반환"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# ===== 응답 관련 유틸리티 =====

def create_success_response(message_key: str = None, data: Any = None, **kwargs) -> Dict:
    """
    성공 응답 생성
    
    Args:
        message_key: 메시지 키
        data: 응답 데이터
        **kwargs: 추가 데이터
        
    Returns:
        응답 딕셔너리
    """
    response = {
        "success": True,
        "message": SUCCESS_MESSAGES.get(message_key, "작업이 완료되었습니다."),
        "timestamp": datetime.now().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    
    response.update(kwargs)
    return response

def create_error_response(message_key: str = None, error_detail: str = None, **kwargs) -> Dict:
    """
    에러 응답 생성
    
    Args:
        message_key: 에러 메시지 키
        error_detail: 상세 에러 내용
        **kwargs: 추가 데이터
        
    Returns:
        에러 응답 딕셔너리
    """
    response = {
        "success": False,
        "error": ERROR_MESSAGES.get(message_key, "알 수 없는 오류가 발생했습니다."),
        "timestamp": datetime.now().isoformat()
    }
    
    if error_detail:
        response["detail"] = error_detail
    
    response.update(kwargs)
    return response

# ===== 환경 관련 유틸리티 =====

def is_production() -> bool:
    """프로덕션 환경인지 확인"""
    return os.getenv("KOYEB_PUBLIC_DOMAIN") is not None

def get_environment() -> str:
    """현재 환경 반환"""
    if is_production():
        return "production"
    elif os.getenv("TESTING"):
        return "testing"
    else:
        return "development"

# ===== 로깅 유틸리티 =====

def log_operation(operation: str, details: Dict = None, success: bool = True) -> None:
    """
    작업 로그 출력
    
    Args:
        operation: 작업 이름
        details: 상세 정보
        success: 성공 여부
    """
    status_icon = "✅" if success else "❌"
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    log_msg = f"{status_icon} [{timestamp}] {operation}"
    
    if details:
        detail_str = ", ".join([f"{k}: {v}" for k, v in details.items()])
        log_msg += f" - {detail_str}"
    
    print(log_msg)

# 모듈 테스트용
if __name__ == "__main__":
    print("🛠️ Utils 모듈 테스트")
    print("=" * 50)
    
    # 파일 검증 테스트
    test_filename = "test document.pdf"
    is_valid, error = validate_file_basic(test_filename, 1024 * 1024)  # 1MB
    print(f"파일 검증: {is_valid} - {error if not is_valid else 'OK'}")
    
    # 파일명 정리 테스트
    dirty_filename = "  ../test file<>.pdf  "
    clean_filename = sanitize_filename(dirty_filename)
    print(f"파일명 정리: '{dirty_filename}' → '{clean_filename}'")
    
    # 환경 확인
    env = get_environment()
    print(f"현재 환경: {env}")
    
    # 응답 생성 테스트
    success_resp = create_success_response("UPLOAD", {"file_count": 1})
    print(f"성공 응답: {success_resp}")
    
    print("\n🎉 Utils 모듈 테스트 완료!")