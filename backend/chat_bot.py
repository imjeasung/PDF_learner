# AI 질의응답 모듈 (RAG 방식)
# AI Provider Manager를 사용하여 PDF 내용을 기반으로 답변을 생성합니다.

import os
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

# AI Provider Manager 임포트
try:
    from ai_providers import get_ai_manager
    from config import settings
    USE_AI_MANAGER = True
except ImportError:
    # 기존 OpenAI 방식으로 폴백
    import openai
    USE_AI_MANAGER = False

# 환경변수 로드
load_dotenv()

class ChatBot:
    """PDF 내용을 기반으로 질의응답을 수행하는 챗봇 클래스입니다."""
    
    def __init__(self, data_folder: str = "data"):
        """
        챗봇을 초기화합니다.
        
        Args:
            data_folder: 데이터가 저장된 폴더
        """
        self.data_folder = data_folder
        self.vector_db_path = os.getenv("VECTOR_DB_PATH", f"{data_folder}/vector_db")
        
        # 필요한 폴더 생성
        Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)
        
        # AI Provider Manager 초기화
        if USE_AI_MANAGER:
            try:
                self.ai_manager = get_ai_manager()
                openai_config = settings.AI_PROVIDERS_CONFIG.get("openai", {})
                self.model = openai_config.get("default_model", "gpt-3.5-turbo")
                self.embedding_model = openai_config.get("embedding_model", "text-embedding-ada-002")
                self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
                self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
                print(f"🤖 챗봇 초기화 완료 (AI Manager 사용, 모델: {self.model})")
            except Exception as e:
                print(f"⚠️ AI Manager 초기화 실패, 기존 방식으로 폴백: {str(e)}")
                self._init_legacy_openai()
        else:
            self._init_legacy_openai()
        
        # ChromaDB 설정
        self.chroma_client = chromadb.PersistentClient(
            path=self.vector_db_path,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # 활성화된 문서들의 컬렉션 저장
        self.active_collections = {}
    
    def _init_legacy_openai(self):
        """기존 OpenAI 방식으로 초기화 (폴백용)"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다!")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.ai_manager = None
        
        print(f"🤖 챗봇 초기화 완료 (레거시 모드, 모델: {self.model})")
    
    def _sanitize_collection_name(self, file_name: str) -> str:
        """
        파일명을 ChromaDB 컬렉션 이름 규칙에 맞게 변환합니다.
        
        Args:
            file_name: 원본 파일명
            
        Returns:
            안전한 컬렉션 이름
        """
        # .pdf 확장자 제거
        clean_name = file_name.replace('.pdf', '')
        
        # 한글과 특수문자를 영문과 숫자로 변환
        # 1. 영문, 숫자, 일부 허용된 특수문자만 남기기
        safe_chars = re.sub(r'[^a-zA-Z0-9._-]', '_', clean_name)
        
        # 2. 연속된 언더스코어를 하나로 합치기
        safe_chars = re.sub(r'_+', '_', safe_chars)
        
        # 3. 시작과 끝의 언더스코어 제거
        safe_chars = safe_chars.strip('_')
        
        # 4. 빈 문자열이거나 너무 짧으면 해시값 사용
        if len(safe_chars) < 3:
            # 원본 파일명의 해시값 생성
            hash_value = hashlib.md5(file_name.encode('utf-8')).hexdigest()[:8]
            safe_chars = f"doc_{hash_value}"
        else:
            # doc_ 접두사 추가
            safe_chars = f"doc_{safe_chars}"
        
        # 5. 길이 제한 (ChromaDB는 512자까지 허용하지만 적당히 제한)
        if len(safe_chars) > 100:
            # 원본 파일명의 해시값으로 단축
            hash_value = hashlib.md5(file_name.encode('utf-8')).hexdigest()[:8]
            safe_chars = f"doc_{safe_chars[:50]}_{hash_value}"
        
        # 6. 최종 검증: 영문/숫자로 시작하고 끝나는지 확인
        if not re.match(r'^[a-zA-Z0-9].*[a-zA-Z0-9]$', safe_chars):
            hash_value = hashlib.md5(file_name.encode('utf-8')).hexdigest()[:8]
            safe_chars = f"doc_{hash_value}"
        
        return safe_chars
    
    def create_vector_database(self, extracted_data: Dict) -> str:
        """
        추출된 PDF 데이터로부터 벡터 데이터베이스를 생성합니다.
        
        Args:
            extracted_data: PDF에서 추출된 데이터
            
        Returns:
            생성된 컬렉션 이름
        """
        try:
            file_name = extracted_data["file_name"]
            collection_name = self._sanitize_collection_name(file_name)
            
            print(f"📊 벡터 DB 생성 시작: {file_name}")
            print(f"  🏷️ 컬렉션 이름: {collection_name}")
            
            # 기존 컬렉션이 있으면 삭제
            try:
                self.chroma_client.delete_collection(name=collection_name)
            except:
                pass  # 컬렉션이 없으면 무시
            
            # 새 컬렉션 생성
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": f"Vector database for {file_name}"}
            )
            
            # 텍스트 청크들 준비
            documents = []
            metadatas = []
            ids = []
            
            # 페이지별로 텍스트 처리
            for page in extracted_data["pages"]:
                page_num = page["page_number"]
                page_text = page["text"].strip()
                
                if page_text:
                    # 페이지 텍스트를 작은 단위로 분할
                    chunks = self._split_page_text(page_text)
                    
                    for i, chunk in enumerate(chunks):
                        if len(chunk.strip()) > 50:  # 너무 짧은 텍스트는 제외
                            doc_id = f"{file_name}_page{page_num}_chunk{i}"
                            
                            documents.append(chunk)
                            metadatas.append({
                                "file_name": file_name,
                                "page_number": page_num,
                                "chunk_index": i,
                                "source": f"페이지 {page_num}"
                            })
                            ids.append(doc_id)
            
            print(f"  📝 총 {len(documents)}개 텍스트 청크 생성")
            
            # 임베딩 생성 및 저장 (배치 단위로 처리)
            batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                batch_docs = documents[i:end_idx]
                batch_metas = metadatas[i:end_idx]
                batch_ids = ids[i:end_idx]
                
                # OpenAI 임베딩 생성
                embeddings = self._generate_embeddings(batch_docs)
                
                # ChromaDB에 저장
                collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                    embeddings=embeddings
                )
                
                print(f"  💾 배치 {i//batch_size + 1} 저장 완료 ({end_idx}/{len(documents)})")
            
            # 컬렉션을 활성화 목록에 추가
            self.active_collections[file_name] = collection_name
            
            print(f"🎉 벡터 DB 생성 완료: {collection_name}")
            return collection_name
            
        except Exception as e:
            print(f"❌ 벡터 DB 생성 실패: {str(e)}")
            raise Exception(f"벡터 DB 생성 실패: {str(e)}")
    
    def _split_page_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """페이지 텍스트를 작은 청크로 분할합니다."""
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                current_chunk += sentence + ". "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """텍스트 리스트의 임베딩을 생성합니다."""
        try:
            # AI Manager 사용 또는 기존 방식 폴백
            if self.ai_manager:
                embedding_result = self.ai_manager.generate_embeddings(
                    texts=texts,
                    model=self.embedding_model
                )
                # EmbeddingResult 객체에서 실제 임베딩 리스트 추출
                return embedding_result.embeddings
            else:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=texts
                )
                
                embeddings = [item.embedding for item in response.data]
                return embeddings
            
        except Exception as e:
            print(f"  ⚠️ 임베딩 생성 실패: {str(e)}")
            # 임시로 빈 임베딩 반환
            embedding_dim = int(os.getenv("EMBEDDING_DIMENSION", "1536"))  # ada-002의 기본 차원
            return [[0.0] * embedding_dim for _ in texts]
    
    def answer_question(self, question: str, file_name: str = None, top_k: int = 3) -> Dict:
        """
        사용자 질문에 대해 PDF 내용을 기반으로 답변을 생성합니다.
        
        Args:
            question: 사용자 질문
            file_name: 검색할 문서명 (None이면 모든 문서 검색)
            top_k: 검색할 관련 문서 개수
            
        Returns:
            답변과 출처 정보
        """
        try:
            print(f"❓ 질문 처리: {question}")
            
            # 관련 문서 검색
            relevant_chunks = self._search_relevant_chunks(question, file_name, top_k)
            
            if not relevant_chunks:
                return {
                    "answer": "죄송합니다. 업로드된 PDF 문서에서 관련 정보를 찾을 수 없습니다.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # AI로 답변 생성
            answer_data = self._generate_answer_with_ai(question, relevant_chunks)
            
            print(f"✅ 답변 생성 완료")
            return answer_data
            
        except Exception as e:
            print(f"❌ 질문 처리 실패: {str(e)}")
            return {
                "answer": f"죄송합니다. 질문 처리 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }
    
    def _search_relevant_chunks(self, question: str, file_name: str = None, top_k: int = 3) -> List[Dict]:
        """질문과 관련된 텍스트 청크들을 검색합니다."""
        try:
            # 질문의 임베딩 생성
            question_embedding = self._generate_embeddings([question])[0]
            
            relevant_chunks = []
            
            # 특정 문서가 지정된 경우
            if file_name and file_name in self.active_collections:
                collection_name = self.active_collections[file_name]
                collection = self.chroma_client.get_collection(name=collection_name)
                
                results = collection.query(
                    query_embeddings=[question_embedding],
                    n_results=top_k
                )
                
                relevant_chunks.extend(self._format_search_results(results))
            
            # 모든 문서 검색
            else:
                for doc_name, collection_name in self.active_collections.items():
                    try:
                        collection = self.chroma_client.get_collection(name=collection_name)
                        
                        results = collection.query(
                            query_embeddings=[question_embedding],
                            n_results=max(1, top_k // len(self.active_collections))
                        )
                        
                        relevant_chunks.extend(self._format_search_results(results))
                    except Exception as e:
                        print(f"  ⚠️ 컬렉션 {collection_name} 검색 실패: {str(e)}")
                        continue
            
            # 유사도 점수로 정렬하고 상위 결과만 반환
            relevant_chunks.sort(key=lambda x: x.get("distance", 1.0))
            return relevant_chunks[:top_k]
            
        except Exception as e:
            print(f"  ⚠️ 검색 실패: {str(e)}")
            return []
    
    def _format_search_results(self, results) -> List[Dict]:
        """ChromaDB 검색 결과를 포맷팅합니다."""
        formatted = []
        
        if results["documents"] and len(results["documents"]) > 0:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []
            
            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                
                formatted.append({
                    "content": doc,
                    "file_name": metadata.get("file_name", "알 수 없음"),
                    "page_number": metadata.get("page_number", "알 수 없음"),
                    "source": metadata.get("source", "알 수 없음"),
                    "distance": distance,
                    "similarity": 1.0 - distance  # 유사도 계산
                })
        
        return formatted
    
    def _generate_answer_with_ai(self, question: str, relevant_chunks: List[Dict]) -> Dict:
        """AI를 사용하여 최종 답변을 생성합니다."""
        try:
            # 컨텍스트 구성
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(relevant_chunks):
                context_parts.append(f"[출처 {i+1}: {chunk['source']}]\n{chunk['content']}")
                sources.append({
                    "file_name": chunk["file_name"],
                    "page_number": chunk["page_number"],
                    "source": chunk["source"],
                    "similarity": round(chunk.get("similarity", 0.0), 3)
                })
            
            context = "\n\n".join(context_parts)
            
            # AI 프롬프트 구성
            prompt = f"""
다음 문서 내용을 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 해주세요.

문서 내용:
{context}

사용자 질문: {question}

답변 시 다음 사항을 지켜주세요:
1. 문서에 있는 정보만을 기반으로 답변하세요
2. 구체적이고 명확하게 설명하세요
3. 문서에 없는 내용은 추측하지 마세요
4. 도움이 되는 추가 설명을 포함하세요

답변:
"""

            # AI Manager 사용 또는 기존 방식 폴백
            if self.ai_manager:
                generation_result = self.ai_manager.generate_text(
                    prompt=prompt,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                # GenerationResult 객체에서 실제 텍스트 추출
                answer = generation_result.text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                answer = response.choices[0].message.content.strip()
            
            # 신뢰도 계산 (유사도 점수들의 평균)
            if relevant_chunks:
                confidence = sum(chunk.get("similarity", 0.0) for chunk in relevant_chunks) / len(relevant_chunks)
            else:
                confidence = 0.0
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": round(confidence, 3),
                "context_used": len(relevant_chunks)
            }
            
        except Exception as e:
            print(f"  ⚠️ AI 답변 생성 실패: {str(e)}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "sources": sources if 'sources' in locals() else [],
                "confidence": 0.0
            }
    
    def get_available_documents(self) -> List[str]:
        """사용 가능한 문서 목록을 반환합니다."""
        return list(self.active_collections.keys())
    
    def remove_document(self, file_name: str) -> bool:
        """
        문서를 챗봇에서 제거합니다.
        
        Args:
            file_name: 제거할 문서명 (확장자 제외)
            
        Returns:
            제거 성공 여부
        """
        try:
            # 활성 컬렉션에서 제거
            if file_name in self.active_collections:
                collection_name = self.active_collections[file_name]
                
                try:
                    # ChromaDB에서 컬렉션 삭제
                    self.chroma_client.delete_collection(name=collection_name)
                    print(f"🗑️ ChromaDB 컬렉션 삭제: {collection_name}")
                except Exception as e:
                    print(f"⚠️ ChromaDB 컬렉션 삭제 실패: {e}")
                
                # 메모리에서 제거
                del self.active_collections[file_name]
                print(f"🧹 문서 메모리에서 제거: {file_name}")
                return True
            else:
                print(f"⚠️ 문서를 찾을 수 없습니다: {file_name}")
                return False
                
        except Exception as e:
            print(f"❌ 문서 제거 실패: {str(e)}")
            return False
    
    def load_document_for_chat(self, file_name: str) -> bool:
        """
        채팅을 위해 문서를 로드합니다.
        
        Args:
            file_name: 로드할 문서명
            
        Returns:
            로드 성공 여부
        """
        try:
            # 추출된 데이터 파일 찾기
            extracted_file = f"{self.data_folder}/extracted/{file_name}_extracted.json"
            
            if not os.path.exists(extracted_file):
                print(f"❌ 추출된 데이터 파일을 찾을 수 없습니다: {extracted_file}")
                return False
            
            # 데이터 로드
            with open(extracted_file, 'r', encoding='utf-8') as f:
                extracted_data = json.load(f)
            
            # 벡터 DB 생성
            self.create_vector_database(extracted_data)
            return True
            
        except Exception as e:
            print(f"❌ 문서 로드 실패: {str(e)}")
            return False

# 편의 함수들
def create_chatbot() -> ChatBot:
    """챗봇 인스턴스를 생성합니다."""
    return ChatBot()

def setup_document_for_chat(file_name: str) -> bool:
    """문서를 채팅용으로 설정합니다."""
    chatbot = create_chatbot()
    return chatbot.load_document_for_chat(file_name)

# 테스트용 메인 함수
if __name__ == "__main__":
    import sys
    import io
    
    # Windows 환경에서 UTF-8 출력 설정
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("🧪 챗봇 테스트 시작...")
    
    try:
        # 챗봇 생성
        chatbot = ChatBot()
        print("✅ 챗봇 초기화 성공")
        
        print("🎉 챗봇 초기화 성공!")
        print("💡 이 모듈은 main.py에서 import하여 사용됩니다.")
        
    except Exception as e:
        print(f"❌ 챗봇 테스트 실패: {str(e)}")
        print("💡 .env 파일에 OPENAI_API_KEY가 올바르게 설정되었는지 확인해주세요.")