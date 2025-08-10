# OpenAI Provider Adapter
# 기존 OpenAI 코드를 새로운 어댑터 패턴으로 래핑

import openai
import os
from typing import Dict, List, Optional, Any
from .base import (
    AIProviderAdapter, 
    ModelInfo, 
    GenerationResult, 
    EmbeddingResult,
    ProviderConnectionError,
    UnsupportedModelError,
    RateLimitError
)

class OpenAIAdapter(AIProviderAdapter):
    """OpenAI API를 위한 어댑터 구현"""
    
    # OpenAI 모델 정보 (실제 API에서 가져올 수도 있지만 안정성을 위해 하드코딩)
    AVAILABLE_MODELS = [
        ModelInfo(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            description="빠르고 효율적인 대화형 AI 모델",
            provider="openai",
            type="text",
            max_tokens=4096,
            cost_per_1k_tokens=0.001,
            supports_streaming=True
        ),
        ModelInfo(
            id="gpt-3.5-turbo-16k",
            name="GPT-3.5 Turbo 16K",
            description="긴 컨텍스트를 지원하는 GPT-3.5",
            provider="openai", 
            type="text",
            max_tokens=16384,
            cost_per_1k_tokens=0.003,
            supports_streaming=True
        ),
        ModelInfo(
            id="gpt-4",
            name="GPT-4",
            description="고성능 AI 모델",
            provider="openai",
            type="text", 
            max_tokens=8192,
            cost_per_1k_tokens=0.03,
            supports_streaming=True
        ),
        ModelInfo(
            id="gpt-4-turbo-preview",
            name="GPT-4 Turbo",
            description="향상된 성능의 GPT-4",
            provider="openai",
            type="text",
            max_tokens=128000,
            cost_per_1k_tokens=0.01,
            supports_streaming=True
        )
    ]
    
    EMBEDDING_MODELS = [
        ModelInfo(
            id="text-embedding-ada-002",
            name="Ada Embedding v2",
            description="범용 임베딩 모델",
            provider="openai",
            type="embedding",
            max_tokens=8191,
            cost_per_1k_tokens=0.0001,
            supports_streaming=False
        ),
        ModelInfo(
            id="text-embedding-3-small",
            name="Embedding v3 Small",
            description="효율적인 임베딩 모델",
            provider="openai",
            type="embedding", 
            max_tokens=8191,
            cost_per_1k_tokens=0.00002,
            supports_streaming=False
        ),
        ModelInfo(
            id="text-embedding-3-large",
            name="Embedding v3 Large",
            description="고성능 임베딩 모델",
            provider="openai",
            type="embedding",
            max_tokens=8191,
            cost_per_1k_tokens=0.00013,
            supports_streaming=False
        )
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        OpenAI 어댑터를 초기화합니다.
        
        Args:
            config: OpenAI 설정 딕셔너리
                    - api_key: OpenAI API 키
                    - default_model: 기본 사용할 모델
                    - default_embedding_model: 기본 임베딩 모델
                    - max_tokens: 기본 최대 토큰 수
                    - temperature: 기본 온도 설정
        """
        config["provider_name"] = "openai"
        super().__init__(config)
        
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.default_model = config.get("default_model", "gpt-3.5-turbo")
        self.default_embedding_model = config.get("default_embedding_model", "text-embedding-ada-002")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
        
        self.client = None
        
    def initialize(self) -> bool:
        """OpenAI 클라이언트를 초기화합니다."""
        try:
            if not self.api_key:
                print("❌ OpenAI API 키가 없습니다.")
                return False
                
            self.client = openai.OpenAI(api_key=self.api_key)
            
            # 간단한 연결 테스트
            test_models = self.client.models.list()
            
            self.is_initialized = True
            print(f"✅ OpenAI 어댑터 초기화 완료 (기본 모델: {self.default_model})")
            return True
            
        except Exception as e:
            print(f"❌ OpenAI 초기화 실패: {str(e)}")
            self.is_initialized = False
            return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """사용 가능한 모델 목록을 반환합니다."""
        return self.AVAILABLE_MODELS + self.EMBEDDING_MODELS
    
    def generate_text(
        self, 
        prompt: str, 
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> GenerationResult:
        """
        텍스트를 생성합니다.
        
        Args:
            prompt: 입력 프롬프트
            model: 사용할 모델 (None이면 기본 모델)
            max_tokens: 최대 토큰 수 (None이면 기본값)
            temperature: 생성 온도 (None이면 기본값)
            **kwargs: 추가 매개변수
            
        Returns:
            생성 결과
        """
        if not self.is_initialized:
            raise ProviderConnectionError("OpenAI 어댑터가 초기화되지 않았습니다.", "openai")
        
        # 기본값 설정
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        # 모델 검증
        text_models = [m for m in self.AVAILABLE_MODELS if m.type == "text"]
        if not any(m.id == model for m in text_models):
            raise UnsupportedModelError(f"지원되지 않는 모델입니다: {model}", "openai")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            generated_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # 비용 계산
            model_info = next((m for m in text_models if m.id == model), None)
            cost = (tokens_used / 1000) * model_info.cost_per_1k_tokens if model_info else 0.0
            
            return GenerationResult(
                text=generated_text,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "response_id": response.id
                }
            )
            
        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI API 사용량 제한: {str(e)}", "openai")
        except Exception as e:
            raise ProviderConnectionError(f"OpenAI API 호출 실패: {str(e)}", "openai")
    
    def generate_embeddings(
        self, 
        texts: List[str], 
        model: str = None
    ) -> EmbeddingResult:
        """
        텍스트 목록의 임베딩을 생성합니다.
        
        Args:
            texts: 임베딩할 텍스트 리스트
            model: 사용할 임베딩 모델 (None이면 기본 모델)
            
        Returns:
            임베딩 결과
        """
        if not self.is_initialized:
            raise ProviderConnectionError("OpenAI 어댑터가 초기화되지 않았습니다.", "openai")
        
        model = model or self.default_embedding_model
        
        # 모델 검증
        embedding_models = [m for m in self.EMBEDDING_MODELS if m.type == "embedding"]
        model_info = next((m for m in embedding_models if m.id == model), None)
        if not model_info:
            raise UnsupportedModelError(f"지원되지 않는 임베딩 모델입니다: {model}", "openai")
        
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # 비용 계산
            cost = (tokens_used / 1000) * model_info.cost_per_1k_tokens
            
            return EmbeddingResult(
                embeddings=embeddings,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                dimension=len(embeddings[0]) if embeddings else 0
            )
            
        except openai.RateLimitError as e:
            raise RateLimitError(f"OpenAI API 사용량 제한: {str(e)}", "openai")
        except Exception as e:
            raise ProviderConnectionError(f"OpenAI 임베딩 API 호출 실패: {str(e)}", "openai")
    
    def is_available(self) -> bool:
        """OpenAI 서비스가 사용 가능한지 확인합니다."""
        if not self.is_initialized or not self.api_key:
            return False
            
        try:
            # 간단한 API 호출로 서비스 상태 확인
            self.client.models.list()
            return True
        except:
            return False
    
    def validate_config(self) -> tuple[bool, str]:
        """OpenAI 어댑터 설정을 검증합니다."""
        base_valid, base_error = super().validate_config()
        if not base_valid:
            return False, base_error
            
        if not self.api_key:
            return False, "OpenAI API 키가 설정되지 않았습니다."
            
        # 모델 검증
        all_models = self.get_available_models()
        if self.default_model and not any(m.id == self.default_model for m in all_models):
            return False, f"기본 모델이 유효하지 않습니다: {self.default_model}"
            
        if self.default_embedding_model and not any(m.id == self.default_embedding_model for m in all_models):
            return False, f"기본 임베딩 모델이 유효하지 않습니다: {self.default_embedding_model}"
        
        return True, ""

# 편의 함수: 기존 코드와의 호환성을 위한 래퍼
def create_openai_adapter(
    api_key: str = None,
    model: str = "gpt-3.5-turbo",
    embedding_model: str = "text-embedding-ada-002",
    max_tokens: int = 1000,
    temperature: float = 0.7
) -> OpenAIAdapter:
    """
    OpenAI 어댑터를 쉽게 생성하는 편의 함수
    
    Args:
        api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
        model: 기본 텍스트 생성 모델
        embedding_model: 기본 임베딩 모델
        max_tokens: 기본 최대 토큰 수
        temperature: 기본 온도 설정
        
    Returns:
        초기화된 OpenAI 어댑터
    """
    config = {
        "api_key": api_key,
        "default_model": model,
        "default_embedding_model": embedding_model,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    adapter = OpenAIAdapter(config)
    adapter.initialize()
    return adapter