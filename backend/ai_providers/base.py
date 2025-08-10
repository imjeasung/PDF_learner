# AI Provider 기본 인터페이스
# 모든 AI 제공업체 어댑터가 구현해야 하는 공통 인터페이스

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class ModelInfo:
    """AI 모델 정보를 담는 데이터 클래스"""
    id: str
    name: str
    description: str
    provider: str
    type: str  # "text", "embedding", "multimodal"
    max_tokens: int
    cost_per_1k_tokens: float = 0.0
    supports_streaming: bool = False
    
@dataclass
class GenerationResult:
    """텍스트 생성 결과를 담는 데이터 클래스"""
    text: str
    model: str
    tokens_used: int
    cost: float = 0.0
    metadata: Dict[str, Any] = None

@dataclass
class EmbeddingResult:
    """임베딩 생성 결과를 담는 데이터 클래스"""
    embeddings: List[List[float]]
    model: str
    tokens_used: int
    cost: float = 0.0
    dimension: int = 0

class AIProviderAdapter(ABC):
    """
    모든 AI 제공업체 어댑터가 구현해야 하는 기본 인터페이스입니다.
    
    이 클래스를 상속받아 각 AI 제공업체(OpenAI, Anthropic, Local 등)의 
    구체적인 구현을 제공합니다.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        AI Provider 어댑터를 초기화합니다.
        
        Args:
            config: 제공업체별 설정 딕셔너리
        """
        self.config = config
        self.provider_name = config.get("provider_name", "unknown")
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        AI 제공업체 클라이언트를 초기화합니다.
        
        Returns:
            초기화 성공 여부
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """
        사용 가능한 모델 목록을 반환합니다.
        
        Returns:
            모델 정보 리스트
        """
        pass
    
    @abstractmethod
    def generate_text(
        self, 
        prompt: str, 
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> GenerationResult:
        """
        텍스트를 생성합니다.
        
        Args:
            prompt: 입력 프롬프트
            model: 사용할 모델 ID (None이면 기본 모델)
            max_tokens: 최대 토큰 수
            temperature: 생성 온도 (0.0-2.0)
            **kwargs: 추가 매개변수
            
        Returns:
            생성 결과
        """
        pass
    
    @abstractmethod
    def generate_embeddings(
        self, 
        texts: List[str], 
        model: str = None
    ) -> EmbeddingResult:
        """
        텍스트 목록의 임베딩을 생성합니다.
        
        Args:
            texts: 임베딩할 텍스트 리스트
            model: 사용할 임베딩 모델 ID (None이면 기본 모델)
            
        Returns:
            임베딩 결과
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        AI 제공업체가 사용 가능한지 확인합니다.
        
        Returns:
            사용 가능 여부
        """
        pass
    
    def get_provider_name(self) -> str:
        """제공업체 이름을 반환합니다."""
        return self.provider_name
    
    def get_cost_estimate(self, tokens: int, model: str = None) -> float:
        """
        예상 비용을 계산합니다.
        
        Args:
            tokens: 토큰 수
            model: 모델 ID
            
        Returns:
            예상 비용 (USD)
        """
        models = self.get_available_models()
        model_info = next((m for m in models if m.id == model), None)
        
        if model_info:
            return (tokens / 1000) * model_info.cost_per_1k_tokens
        return 0.0
    
    def validate_config(self) -> tuple[bool, str]:
        """
        설정이 유효한지 검증합니다.
        
        Returns:
            (유효성, 오류 메시지)
        """
        required_fields = ["provider_name"]
        
        for field in required_fields:
            if field not in self.config:
                return False, f"필수 설정 '{field}'가 누락되었습니다."
        
        return True, ""

class AIProviderError(Exception):
    """AI Provider 관련 오류를 나타내는 예외 클래스"""
    
    def __init__(self, message: str, provider: str = None, error_code: str = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code

class UnsupportedModelError(AIProviderError):
    """지원되지 않는 모델을 사용하려 할 때 발생하는 예외"""
    pass

class ProviderConnectionError(AIProviderError):
    """AI 제공업체와의 연결에 실패했을 때 발생하는 예외"""
    pass

class RateLimitError(AIProviderError):
    """API 사용량 제한에 도달했을 때 발생하는 예외"""
    pass