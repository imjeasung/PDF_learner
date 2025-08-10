# 프로젝트 설정 관리 모듈
# 모든 설정값을 중앙에서 관리하여 하드코딩을 제거합니다.

import os
from typing import List
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class Settings:
    """프로젝트 설정 클래스 - 모든 설정값을 중앙 관리"""
    
    # ===== API 설정 =====
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # ===== 파일 및 폴더 경로 설정 =====
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    DATA_FOLDER: str = os.getenv("DATA_FOLDER", "data")
    STATIC_FOLDER: str = os.getenv("STATIC_FOLDER", "static")
    
    # 하위 폴더 경로들
    @property
    def EXTRACTED_FOLDER(self) -> str:
        return f"{self.DATA_FOLDER}/extracted"
    
    @property
    def SUMMARIES_FOLDER(self) -> str:
        return f"{self.DATA_FOLDER}/summaries"
    
    @property
    def VECTOR_DB_FOLDER(self) -> str:
        return f"{self.DATA_FOLDER}/vector_db"
    
    # ===== 서버 설정 =====
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ===== 배포 환경 설정 =====
    KOYEB_PUBLIC_DOMAIN: str = os.getenv("KOYEB_PUBLIC_DOMAIN")
    IS_PRODUCTION: bool = KOYEB_PUBLIC_DOMAIN is not None
    
    # ===== CORS 설정 =====
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """환경에 따른 CORS 허용 도메인 설정"""
        base_origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]
        
        # 환경변수에서 추가 도메인 설정
        env_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        env_origins = [origin.strip() for origin in env_origins if origin.strip()]
        
        # Koyeb 배포 도메인 추가
        if self.KOYEB_PUBLIC_DOMAIN:
            base_origins.extend([
                f"https://{self.KOYEB_PUBLIC_DOMAIN}",
                f"http://{self.KOYEB_PUBLIC_DOMAIN}"
            ])
        
        # 환경변수 도메인 추가
        base_origins.extend(env_origins)
        
        return list(set(base_origins))  # 중복 제거
    
    # ===== 파일 제한 설정 =====
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    
    # ===== 데이터베이스 설정 =====
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./pdf_learner.db")
    
    # ===== AI 처리 설정 =====
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    # ===== 벡터 DB 설정 =====
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", f"{DATA_FOLDER}/vector_db")
    
    # ===== AI Provider 설정 =====
    # 기본 AI 제공업체 설정
    DEFAULT_AI_PROVIDER: str = os.getenv("DEFAULT_AI_PROVIDER", "openai")
    
    # OpenAI 설정 (기존 호환성 유지)
    @property
    def OPENAI_CONFIG(self) -> dict:
        """OpenAI Provider 설정 반환"""
        return {
            "provider_name": "openai",
            "api_key": self.OPENAI_API_KEY,
            "default_model": self.OPENAI_MODEL,
            "default_embedding_model": self.OPENAI_EMBEDDING_MODEL,
            "max_tokens": self.MAX_TOKENS,
            "temperature": self.TEMPERATURE
        }
    
    # 다중 AI Provider 설정
    @property
    def AI_PROVIDERS_CONFIG(self) -> dict:
        """모든 AI Provider 설정 반환"""
        providers = {}
        
        # OpenAI 설정 (API 키가 있을 때만)
        if self.OPENAI_API_KEY:
            providers["openai"] = self.OPENAI_CONFIG
        
        # Anthropic 설정 (환경변수가 있을 때)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            providers["anthropic"] = {
                "provider_name": "anthropic",
                "api_key": anthropic_key,
                "default_model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "1000")),
                "temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
            }
        
        # Local LLM 설정 (환경변수가 있을 때)
        local_model_path = os.getenv("LOCAL_MODEL_PATH")
        if local_model_path:
            providers["local"] = {
                "provider_name": "local",
                "model_path": local_model_path,
                "default_model": os.getenv("LOCAL_MODEL", "llama2"),
                "max_tokens": int(os.getenv("LOCAL_MAX_TOKENS", "1000")),
                "temperature": float(os.getenv("LOCAL_TEMPERATURE", "0.7"))
            }
        
        return providers
    
    # 지원하는 모델 목록 (확장 가능)
    @property
    def SUPPORTED_TEXT_MODELS(self) -> dict:
        """지원하는 텍스트 생성 모델 목록"""
        return {
            "openai": [
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k", 
                "gpt-4",
                "gpt-4-turbo-preview",
                "gpt-4o",
                "gpt-4o-mini"
            ],
            "anthropic": [
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229",
                "claude-3-5-sonnet-20241022"
            ],
            "local": [
                "llama2",
                "llama3",
                "mistral-7b",
                "gemma-7b",
                "qwen2-7b"
            ]
        }
    
    @property
    def SUPPORTED_EMBEDDING_MODELS(self) -> dict:
        """지원하는 임베딩 모델 목록"""
        return {
            "openai": [
                "text-embedding-ada-002",
                "text-embedding-3-small",
                "text-embedding-3-large"
            ],
            "local": [
                "all-MiniLM-L6-v2",
                "all-mpnet-base-v2",
                "multilingual-e5-large"
            ]
        }
    
    # AI Provider 기능 플래그
    ENABLE_MULTI_PROVIDER: bool = os.getenv("ENABLE_MULTI_PROVIDER", "True").lower() == "true"
    ENABLE_LOCAL_LLM: bool = os.getenv("ENABLE_LOCAL_LLM", "False").lower() == "true"
    ENABLE_MODEL_SWITCHING: bool = os.getenv("ENABLE_MODEL_SWITCHING", "True").lower() == "true"
    
    def validate_required_settings(self) -> None:
        """필수 설정값들이 올바르게 설정되었는지 검증"""
        errors = []
        warnings = []
        
        # AI Provider 설정 검증
        providers_config = self.AI_PROVIDERS_CONFIG
        if not providers_config:
            warnings.append("No AI providers configured. At least one provider is recommended.")
        
        # 기본 제공업체 검증
        if self.DEFAULT_AI_PROVIDER not in providers_config:
            if providers_config:
                # 사용 가능한 첫 번째 제공업체로 대체
                available_provider = list(providers_config.keys())[0]
                warnings.append(f"Default provider '{self.DEFAULT_AI_PROVIDER}' not available. Using '{available_provider}' instead.")
            else:
                errors.append(f"Default provider '{self.DEFAULT_AI_PROVIDER}' not configured and no alternatives available")
        
        # OpenAI 설정 검증 (OpenAI가 설정된 경우만)
        if "openai" in providers_config:
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required when OpenAI provider is enabled")
        
        # Anthropic 설정 검증
        if "anthropic" in providers_config:
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_key:
                errors.append("ANTHROPIC_API_KEY is required when Anthropic provider is enabled")
        
        # 프로덕션 환경 검증
        if self.IS_PRODUCTION:
            if not self.KOYEB_PUBLIC_DOMAIN:
                errors.append("KOYEB_PUBLIC_DOMAIN is required for production")
        
        # 파일 크기 제한 검증
        if self.MAX_FILE_SIZE_MB <= 0:
            errors.append("MAX_FILE_SIZE_MB must be greater than 0")
        
        # AI 설정 검증
        if self.CHUNK_SIZE <= 0:
            errors.append("CHUNK_SIZE must be greater than 0")
        
        if self.CHUNK_OVERLAP < 0:
            errors.append("CHUNK_OVERLAP must be non-negative")
        
        if self.TEMPERATURE < 0 or self.TEMPERATURE > 2:
            errors.append("TEMPERATURE must be between 0 and 2")
        
        # 경고 출력
        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"   - {warning}")
        
        # 오류 처리
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)
    
    def get_folder_paths(self) -> List[str]:
        """생성해야 할 모든 폴더 경로 목록을 반환"""
        return [
            self.UPLOAD_FOLDER,
            self.DATA_FOLDER,
            self.EXTRACTED_FOLDER,
            self.SUMMARIES_FOLDER,
            self.VECTOR_DB_FOLDER,
            self.STATIC_FOLDER,
            "backend"  # backend 폴더도 포함
        ]
    
    def display_settings(self) -> str:
        """현재 설정값들을 표시용 문자열로 반환 (민감정보 제외)"""
        providers_config = self.AI_PROVIDERS_CONFIG
        
        # AI Provider 정보
        provider_info = []
        for name, config in providers_config.items():
            has_key = "api_key" in config and bool(config["api_key"])
            provider_info.append(f"- {name.upper()}: {'✅ Configured' if has_key else '❌ No API Key'}")
        
        if not provider_info:
            provider_info.append("- No providers configured")
        
        return f"""
PDF Learner Settings:
===================
Environment: {'Production' if self.IS_PRODUCTION else 'Development'}
Host: {self.HOST}:{self.PORT}
Debug Mode: {self.DEBUG}

Folders:
- Upload: {self.UPLOAD_FOLDER}
- Data: {self.DATA_FOLDER}
- Static: {self.STATIC_FOLDER}

AI Provider Settings:
- Default Provider: {self.DEFAULT_AI_PROVIDER}
- Multi-Provider: {'Enabled' if self.ENABLE_MULTI_PROVIDER else 'Disabled'}
- Model Switching: {'Enabled' if self.ENABLE_MODEL_SWITCHING else 'Disabled'}
- Local LLM: {'Enabled' if self.ENABLE_LOCAL_LLM else 'Disabled'}

Configured Providers:
{chr(10).join(provider_info)}

AI Processing:
- Chunk Size: {self.CHUNK_SIZE}
- Temperature: {self.TEMPERATURE}
- Embedding Batch: {self.EMBEDDING_BATCH_SIZE}

File Limits:
- Max Size: {self.MAX_FILE_SIZE_MB}MB

CORS Origins: {len(self.ALLOWED_ORIGINS)} domains configured
Database: {self.DATABASE_URL}
        """.strip()

# 전역 설정 인스턴스
settings = Settings()

# 설정 검증 함수
def validate_settings() -> None:
    """설정값 검증을 수행합니다."""
    try:
        settings.validate_required_settings()
        print("✅ 설정 검증 완료")
    except ValueError as e:
        print(f"❌ 설정 검증 실패:\n{e}")
        raise

# 설정 정보 출력 함수
def print_settings() -> None:
    """현재 설정 정보를 출력합니다."""
    print(settings.display_settings())

# 모듈 테스트용
if __name__ == "__main__":
    print("🔧 Config 모듈 테스트")
    print("=" * 50)
    
    try:
        # 설정 검증
        validate_settings()
        
        # 설정 정보 출력
        print_settings()
        
        print("\n🎉 Config 모듈 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ Config 모듈 테스트 실패: {e}")