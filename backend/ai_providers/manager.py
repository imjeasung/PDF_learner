# AI Provider Manager
# 여러 AI 제공업체를 관리하고 동적으로 전환할 수 있는 매니저 클래스

import os
from typing import Dict, List, Optional, Any, Union
from .base import (
    AIProviderAdapter, 
    ModelInfo, 
    GenerationResult, 
    EmbeddingResult,
    AIProviderError,
    UnsupportedModelError
)
from .openai_adapter import OpenAIAdapter

class AIProviderManager:
    """
    여러 AI 제공업체를 관리하는 매니저 클래스
    
    이 클래스는 다양한 AI 제공업체(OpenAI, Anthropic, Local 등)를 
    통합적으로 관리하고 동적으로 전환할 수 있게 해줍니다.
    """
    
    def __init__(self):
        self.providers: Dict[str, AIProviderAdapter] = {}
        self.current_provider: Optional[str] = None
        self.current_text_model: Optional[str] = None
        self.current_embedding_model: Optional[str] = None
        
        # 사용 통계
        self.usage_stats = {
            "total_text_requests": 0,
            "total_embedding_requests": 0,
            "total_tokens_used": 0,
            "total_cost": 0.0,
            "provider_stats": {}
        }
    
    def register_provider(self, name: str, adapter: AIProviderAdapter) -> bool:
        """
        새로운 AI 제공업체를 등록합니다.
        
        Args:
            name: 제공업체 이름
            adapter: AI 제공업체 어댑터
            
        Returns:
            등록 성공 여부
        """
        try:
            # 설정 검증
            is_valid, error = adapter.validate_config()
            if not is_valid:
                print(f"❌ {name} 제공업체 등록 실패: {error}")
                return False
            
            # 초기화 시도
            if not adapter.initialize():
                print(f"❌ {name} 제공업체 초기화 실패")
                return False
            
            self.providers[name] = adapter
            
            # 통계 초기화
            self.usage_stats["provider_stats"][name] = {
                "text_requests": 0,
                "embedding_requests": 0,
                "tokens_used": 0,
                "cost": 0.0
            }
            
            # 첫 번째 제공업체면 기본으로 설정
            if not self.current_provider:
                self.switch_provider(name)
            
            print(f"✅ {name} 제공업체 등록 완료")
            return True
            
        except Exception as e:
            print(f"❌ {name} 제공업체 등록 중 오류: {str(e)}")
            return False
    
    def switch_provider(self, provider_name: str) -> bool:
        """
        현재 사용할 AI 제공업체를 변경합니다.
        
        Args:
            provider_name: 변경할 제공업체 이름
            
        Returns:
            변경 성공 여부
        """
        if provider_name not in self.providers:
            print(f"❌ 등록되지 않은 제공업체: {provider_name}")
            return False
        
        adapter = self.providers[provider_name]
        if not adapter.is_available():
            print(f"❌ 사용할 수 없는 제공업체: {provider_name}")
            return False
        
        self.current_provider = provider_name
        
        # 기본 모델 설정
        models = adapter.get_available_models()
        text_models = [m for m in models if m.type == "text"]
        embedding_models = [m for m in models if m.type == "embedding"]
        
        if text_models:
            self.current_text_model = text_models[0].id
        if embedding_models:
            self.current_embedding_model = embedding_models[0].id
        
        print(f"✅ 현재 제공업체: {provider_name}")
        return True
    
    def get_current_provider(self) -> Optional[AIProviderAdapter]:
        """현재 활성화된 제공업체 어댑터를 반환합니다."""
        if self.current_provider and self.current_provider in self.providers:
            return self.providers[self.current_provider]
        return None
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공업체 목록을 반환합니다."""
        return [name for name, adapter in self.providers.items() if adapter.is_available()]
    
    def get_all_models(self) -> Dict[str, List[ModelInfo]]:
        """모든 제공업체의 모델 정보를 반환합니다."""
        all_models = {}
        for name, adapter in self.providers.items():
            if adapter.is_available():
                all_models[name] = adapter.get_available_models()
        return all_models
    
    def get_available_text_models(self) -> List[Dict[str, Any]]:
        """현재 사용 가능한 텍스트 생성 모델들을 반환합니다."""
        models = []
        for provider_name, adapter in self.providers.items():
            if adapter.is_available():
                provider_models = adapter.get_available_models()
                for model in provider_models:
                    if model.type == "text":
                        models.append({
                            "id": f"{provider_name}:{model.id}",
                            "name": f"{model.name} ({provider_name})",
                            "description": model.description,
                            "provider": provider_name,
                            "model_id": model.id,
                            "max_tokens": model.max_tokens,
                            "cost_per_1k": model.cost_per_1k_tokens
                        })
        return models
    
    def get_available_embedding_models(self) -> List[Dict[str, Any]]:
        """현재 사용 가능한 임베딩 모델들을 반환합니다."""
        models = []
        for provider_name, adapter in self.providers.items():
            if adapter.is_available():
                provider_models = adapter.get_available_models()
                for model in provider_models:
                    if model.type == "embedding":
                        models.append({
                            "id": f"{provider_name}:{model.id}",
                            "name": f"{model.name} ({provider_name})",
                            "description": model.description,
                            "provider": provider_name,
                            "model_id": model.id,
                            "dimension": model.max_tokens,  # 임베딩 차원
                            "cost_per_1k": model.cost_per_1k_tokens
                        })
        return models
    
    def set_text_model(self, model_spec: str) -> bool:
        """
        텍스트 생성에 사용할 모델을 설정합니다.
        
        Args:
            model_spec: "provider:model_id" 형식 또는 단순 "model_id"
            
        Returns:
            설정 성공 여부
        """
        try:
            if ":" in model_spec:
                provider_name, model_id = model_spec.split(":", 1)
                if provider_name not in self.providers:
                    return False
                self.switch_provider(provider_name)
            else:
                model_id = model_spec
            
            # 현재 제공업체에서 모델 검증
            current_adapter = self.get_current_provider()
            if not current_adapter:
                return False
            
            models = current_adapter.get_available_models()
            text_models = [m for m in models if m.type == "text" and m.id == model_id]
            
            if text_models:
                self.current_text_model = model_id
                print(f"✅ 텍스트 모델 설정: {model_id}")
                return True
            
            return False
            
        except Exception:
            return False
    
    def set_embedding_model(self, model_spec: str) -> bool:
        """
        임베딩에 사용할 모델을 설정합니다.
        
        Args:
            model_spec: "provider:model_id" 형식 또는 단순 "model_id"
            
        Returns:
            설정 성공 여부
        """
        try:
            if ":" in model_spec:
                provider_name, model_id = model_spec.split(":", 1)
                if provider_name not in self.providers:
                    return False
                # 임베딩은 별도 제공업체 사용 가능
            else:
                model_id = model_spec
            
            # 현재 제공업체에서 모델 검증
            current_adapter = self.get_current_provider()
            if not current_adapter:
                return False
            
            models = current_adapter.get_available_models()
            embedding_models = [m for m in models if m.type == "embedding" and m.id == model_id]
            
            if embedding_models:
                self.current_embedding_model = model_id
                print(f"✅ 임베딩 모델 설정: {model_id}")
                return True
            
            return False
            
        except Exception:
            return False
    
    def generate_text(
        self, 
        prompt: str, 
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> GenerationResult:
        """
        현재 설정된 제공업체와 모델로 텍스트를 생성합니다.
        
        Args:
            prompt: 입력 프롬프트
            model: 사용할 모델 (None이면 현재 설정된 모델)
            max_tokens: 최대 토큰 수
            temperature: 생성 온도
            **kwargs: 추가 매개변수
            
        Returns:
            생성 결과
        """
        current_adapter = self.get_current_provider()
        if not current_adapter:
            raise AIProviderError("활성화된 AI 제공업체가 없습니다.")
        
        model = model or self.current_text_model
        if not model:
            raise UnsupportedModelError("설정된 텍스트 모델이 없습니다.")
        
        try:
            result = current_adapter.generate_text(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # 사용 통계 업데이트
            self._update_usage_stats("text", result.tokens_used, result.cost)
            
            return result
            
        except Exception as e:
            raise AIProviderError(f"텍스트 생성 실패: {str(e)}", self.current_provider)
    
    def generate_embeddings(
        self, 
        texts: List[str], 
        model: str = None
    ) -> EmbeddingResult:
        """
        현재 설정된 제공업체와 모델로 임베딩을 생성합니다.
        
        Args:
            texts: 임베딩할 텍스트 리스트
            model: 사용할 모델 (None이면 현재 설정된 모델)
            
        Returns:
            임베딩 결과
        """
        current_adapter = self.get_current_provider()
        if not current_adapter:
            raise AIProviderError("활성화된 AI 제공업체가 없습니다.")
        
        model = model or self.current_embedding_model
        if not model:
            raise UnsupportedModelError("설정된 임베딩 모델이 없습니다.")
        
        try:
            result = current_adapter.generate_embeddings(texts=texts, model=model)
            
            # 사용 통계 업데이트
            self._update_usage_stats("embedding", result.tokens_used, result.cost)
            
            return result
            
        except Exception as e:
            raise AIProviderError(f"임베딩 생성 실패: {str(e)}", self.current_provider)
    
    def _update_usage_stats(self, request_type: str, tokens_used: int, cost: float):
        """사용 통계를 업데이트합니다."""
        # 전체 통계
        if request_type == "text":
            self.usage_stats["total_text_requests"] += 1
        elif request_type == "embedding":
            self.usage_stats["total_embedding_requests"] += 1
        
        self.usage_stats["total_tokens_used"] += tokens_used
        self.usage_stats["total_cost"] += cost
        
        # 제공업체별 통계
        if self.current_provider:
            provider_stats = self.usage_stats["provider_stats"][self.current_provider]
            if request_type == "text":
                provider_stats["text_requests"] += 1
            elif request_type == "embedding":
                provider_stats["embedding_requests"] += 1
            
            provider_stats["tokens_used"] += tokens_used
            provider_stats["cost"] += cost
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """사용 통계를 반환합니다."""
        return self.usage_stats.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """현재 매니저 상태를 반환합니다."""
        return {
            "current_provider": self.current_provider,
            "current_text_model": self.current_text_model,
            "current_embedding_model": self.current_embedding_model,
            "available_providers": self.get_available_providers(),
            "total_providers": len(self.providers),
            "usage_stats": self.usage_stats
        }

# 전역 매니저 인스턴스 (싱글톤 패턴)
_global_manager: Optional[AIProviderManager] = None

def get_ai_manager() -> AIProviderManager:
    """전역 AI 매니저 인스턴스를 반환합니다."""
    global _global_manager
    if _global_manager is None:
        _global_manager = AIProviderManager()
        
        # config.py에서 설정 가져오기
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from config import settings
            
            # 설정된 모든 제공업체 등록
            providers_config = settings.AI_PROVIDERS_CONFIG
            
            for provider_name, config in providers_config.items():
                try:
                    if provider_name == "openai":
                        adapter = OpenAIAdapter(config)
                        _global_manager.register_provider(provider_name, adapter)
                        print(f"✅ {provider_name} 제공업체 등록 완료")
                    
                    # 추후 다른 제공업체들도 여기에 추가
                    # elif provider_name == "anthropic":
                    #     from .anthropic_adapter import AnthropicAdapter
                    #     adapter = AnthropicAdapter(config)
                    #     _global_manager.register_provider(provider_name, adapter)
                    
                except Exception as e:
                    print(f"⚠️ {provider_name} 제공업체 등록 실패: {str(e)}")
            
            # 기본 제공업체 설정
            if settings.DEFAULT_AI_PROVIDER in providers_config:
                _global_manager.switch_provider(settings.DEFAULT_AI_PROVIDER)
            
        except Exception as e:
            print(f"⚠️ AI Provider 설정 로드 실패: {str(e)}")
            
            # 폴백: 환경변수 직접 사용
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                try:
                    openai_config = {
                        "api_key": openai_key,
                        "default_model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                        "default_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
                        "max_tokens": int(os.getenv("MAX_TOKENS", "1000")),
                        "temperature": float(os.getenv("TEMPERATURE", "0.7"))
                    }
                    
                    openai_adapter = OpenAIAdapter(openai_config)
                    _global_manager.register_provider("openai", openai_adapter)
                    print("✅ 폴백: OpenAI 제공업체 등록 완료")
                    
                except Exception as e2:
                    print(f"⚠️ 폴백 OpenAI 등록도 실패: {str(e2)}")
    
    return _global_manager

# 편의 함수들
def get_available_text_models() -> List[Dict[str, Any]]:
    """사용 가능한 텍스트 모델 목록을 반환합니다."""
    return get_ai_manager().get_available_text_models()

def get_available_embedding_models() -> List[Dict[str, Any]]:
    """사용 가능한 임베딩 모델 목록을 반환합니다."""
    return get_ai_manager().get_available_embedding_models()

def switch_ai_provider(provider_name: str) -> bool:
    """AI 제공업체를 변경합니다."""
    return get_ai_manager().switch_provider(provider_name)

def set_ai_text_model(model_spec: str) -> bool:
    """텍스트 생성 모델을 설정합니다."""
    return get_ai_manager().set_text_model(model_spec)

def set_ai_embedding_model(model_spec: str) -> bool:
    """임베딩 모델을 설정합니다."""
    return get_ai_manager().set_embedding_model(model_spec)