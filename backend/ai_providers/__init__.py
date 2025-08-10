# AI Providers 패키지
# 다양한 AI 모델 제공업체를 지원하는 어댑터 패턴 구현

from .base import AIProviderAdapter, ModelInfo, GenerationResult, EmbeddingResult
from .openai_adapter import OpenAIAdapter, create_openai_adapter
from .manager import (
    AIProviderManager, 
    get_ai_manager,
    get_available_text_models,
    get_available_embedding_models,
    switch_ai_provider,
    set_ai_text_model,
    set_ai_embedding_model
)

__all__ = [
    'AIProviderAdapter', 
    'ModelInfo', 
    'GenerationResult', 
    'EmbeddingResult',
    'OpenAIAdapter',
    'create_openai_adapter',
    'AIProviderManager',
    'get_ai_manager',
    'get_available_text_models',
    'get_available_embedding_models', 
    'switch_ai_provider',
    'set_ai_text_model',
    'set_ai_embedding_model'
]