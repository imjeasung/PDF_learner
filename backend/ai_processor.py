# AI 기반 텍스트 분석 및 커리큘럼 생성 모듈
# AI Provider Manager를 사용하여 PDF 내용을 분석하고 학습 커리큘럼을 생성합니다.

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

class AIProcessor:
    """AI를 사용하여 텍스트 분석 및 커리큘럼 생성을 담당하는 클래스입니다."""
    
    def __init__(self, data_folder: str = "data"):
        """
        AI 처리기를 초기화합니다.
        
        Args:
            data_folder: 처리된 데이터를 저장할 폴더
        """
        self.data_folder = data_folder
        self.summaries_folder = f"{data_folder}/summaries"
        
        # 필요한 폴더 생성
        Path(self.summaries_folder).mkdir(parents=True, exist_ok=True)
        
        # AI Provider Manager 초기화
        if USE_AI_MANAGER:
            try:
                self.ai_manager = get_ai_manager()
                self.model = settings.AI_PROVIDERS_CONFIG.get("openai", {}).get("default_model", "gpt-3.5-turbo")
                self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
                self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
                print(f"🤖 AI 처리기 초기화 완료 (AI Manager 사용, 모델: {self.model})")
            except Exception as e:
                print(f"⚠️ AI Manager 초기화 실패, 기존 방식으로 폴백: {str(e)}")
                self._init_legacy_openai()
        else:
            self._init_legacy_openai()
        
        # 텍스트 분할 설정
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    def _init_legacy_openai(self):
        """기존 OpenAI 방식으로 초기화 (폴백용)"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            try:
                raise ValueError("❌ OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다!")
            except UnicodeEncodeError:
                raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다!")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.ai_manager = None
        
        try:
            print(f"🤖 AI 처리기 초기화 완료 (레거시 모드, 모델: {self.model})")
        except UnicodeEncodeError:
            print(f"AI 처리기 초기화 완료 (레거시 모드, 모델: {self.model})")
    
    def create_curriculum(self, extracted_data: Dict) -> Dict:
        """
        추출된 PDF 데이터로부터 학습 커리큘럼을 생성합니다.
        
        Args:
            extracted_data: PDF에서 추출된 데이터
            
        Returns:
            생성된 커리큘럼 데이터
        """
        try:
            file_name = extracted_data["file_name"]
            print(f"📚 커리큘럼 생성 시작: {file_name}")
            
            # 1단계: 텍스트를 의미 있는 단위로 분할
            chunks = self._split_text_into_chunks(extracted_data["full_text"])
            print(f"  📝 텍스트를 {len(chunks)}개 덩어리로 분할 완료")
            
            # 2단계: 기존 목차가 있으면 활용, 없으면 AI로 생성
            curriculum_structure = self._create_curriculum_structure(
                extracted_data["toc"], 
                chunks,
                extracted_data["total_pages"]
            )
            
            # 3단계: 각 섹션별로 요약, 키워드, 질문 생성
            curriculum_content = self._generate_section_content(chunks, curriculum_structure)
            
            # 4단계: 최종 커리큘럼 구성
            final_curriculum = {
                "file_name": file_name,
                "total_pages": extracted_data["total_pages"],
                "total_chunks": len(chunks),
                "structure": curriculum_structure,
                "content": curriculum_content,
                "metadata": {
                    "created_by": "AI Processor",
                    "model_used": self.model,
                    "chunks_processed": len(chunks)
                }
            }
            
            # 5단계: 결과 저장
            self._save_curriculum(final_curriculum, file_name)
            
            print(f"🎉 커리큘럼 생성 완료: {file_name}")
            return final_curriculum
            
        except Exception as e:
            print(f"❌ 커리큘럼 생성 중 오류: {str(e)}")
            raise Exception(f"AI 처리 실패: {str(e)}")
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """텍스트를 의미 있는 단위로 분할합니다."""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            chunks = text_splitter.split_text(text)
            return [chunk.strip() for chunk in chunks if chunk.strip()]
            
        except Exception as e:
            print(f"  ⚠️ 텍스트 분할 중 오류: {str(e)}")
            # 간단한 분할로 대체
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
    
    def _create_curriculum_structure(self, existing_toc: List[Dict], chunks: List[str], total_pages: int) -> List[Dict]:
        """커리큘럼 구조를 생성합니다."""
        try:
            if existing_toc and len(existing_toc) > 0:
                print("  📋 기존 목차를 활용하여 구조 생성")
                return self._use_existing_toc(existing_toc)
            else:
                print("  🤖 AI를 사용하여 새로운 구조 생성")
                return self._generate_ai_structure(chunks[:3])  # 처음 3개 덩어리로 구조 생성
                
        except Exception as e:
            print(f"  ⚠️ 구조 생성 중 오류: {str(e)}")
            # 기본 구조 반환
            return self._create_default_structure(len(chunks))
    
    def _use_existing_toc(self, toc: List[Dict]) -> List[Dict]:
        """기존 목차를 커리큘럼 구조로 변환합니다."""
        structure = []
        for i, item in enumerate(toc):
            structure.append({
                "section_id": f"section_{i+1}",
                "title": item["title"],
                "level": item["level"],
                "page": item["page"],
                "chunk_range": None  # 나중에 설정
            })
        return structure
    
    def _generate_ai_structure(self, sample_chunks: List[str]) -> List[Dict]:
        """AI를 사용하여 커리큘럼 구조를 생성합니다."""
        try:
            # 샘플 텍스트 준비
            sample_text = "\n\n".join(sample_chunks[:3])
            if len(sample_text) > 2000:
                sample_text = sample_text[:2000] + "..."
            
            prompt = f"""
다음 문서의 내용을 바탕으로 학습에 적합한 목차 구조를 3-5개 섹션으로 나누어 생성해주세요.

문서 내용:
{sample_text}

다음 형식으로 응답해주세요:
1. [섹션 제목]
2. [섹션 제목] 
3. [섹션 제목]
...

각 섹션은 학습자가 단계적으로 이해할 수 있도록 논리적 순서로 배열해주세요.
"""

            # AI Manager 사용 또는 기존 방식 폴백
            if self.ai_manager:
                generation_result = self.ai_manager.generate_text(
                    prompt=prompt,
                    model=self.model,
                    max_tokens=500,
                    temperature=self.temperature
                )
                # GenerationResult 객체에서 실제 텍스트 추출
                ai_response = generation_result.text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=self.temperature
                )
                ai_response = response.choices[0].message.content.strip()
            
            return self._parse_ai_structure_response(ai_response)
            
        except Exception as e:
            print(f"    ⚠️ AI 구조 생성 실패: {str(e)}")
            return self._create_default_structure(5)
    
    def _parse_ai_structure_response(self, ai_response: str) -> List[Dict]:
        """AI 응답을 구조화된 데이터로 변환합니다."""
        structure = []
        lines = ai_response.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # 번호나 대시로 시작하는 줄을 섹션으로 인식
                title = line.split('.', 1)[-1].strip() if '.' in line else line.strip('- ')
                if title:
                    structure.append({
                        "section_id": f"section_{i+1}",
                        "title": title,
                        "level": 1,
                        "page": None,
                        "chunk_range": None
                    })
        
        return structure if structure else self._create_default_structure(3)
    
    def _create_default_structure(self, num_sections: int) -> List[Dict]:
        """기본 구조를 생성합니다."""
        structure = []
        section_names = ["도입", "주요 내용", "심화 학습", "결론", "참고사항"]
        
        for i in range(min(num_sections, len(section_names))):
            structure.append({
                "section_id": f"section_{i+1}",
                "title": section_names[i],
                "level": 1,
                "page": None,
                "chunk_range": None
            })
        
        return structure
    
    def _generate_section_content(self, chunks: List[str], structure: List[Dict]) -> Dict:
        """각 섹션별로 요약, 키워드, 질문을 생성합니다."""
        content = {}
        chunks_per_section = max(1, len(chunks) // len(structure))
        
        for i, section in enumerate(structure):
            section_id = section["section_id"]
            
            # 해당 섹션의 텍스트 덩어리들 할당
            start_idx = i * chunks_per_section
            end_idx = min((i + 1) * chunks_per_section, len(chunks))
            section_chunks = chunks[start_idx:end_idx]
            
            print(f"  🔍 섹션 '{section['title']}' 처리 중... ({len(section_chunks)}개 덩어리)")
            
            # AI로 섹션 내용 생성
            section_content = self._process_section_with_ai(section_chunks, section["title"])
            content[section_id] = section_content
        
        return content
    
    def _process_section_with_ai(self, chunks: List[str], section_title: str) -> Dict:
        """AI를 사용하여 섹션 내용을 처리합니다."""
        try:
            # 섹션의 모든 텍스트 합치기
            section_text = "\n\n".join(chunks)
            if len(section_text) > 3000:  # 너무 길면 자르기
                section_text = section_text[:3000] + "..."
            
            prompt = f"""
다음은 "{section_title}" 섹션의 내용입니다. 학습자를 위해 다음 정보를 생성해주세요:

내용:
{section_text}

다음 형식으로 응답해주세요:

[요약]
(이 섹션의 핵심 내용을 2-3문장으로 요약)

[키워드]
(핵심 키워드 5개를 쉼표로 구분)

[예상질문]
1. (이해도 확인 질문)
2. (응용 질문)  
3. (심화 질문)
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
                ai_response = generation_result.text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                ai_response = response.choices[0].message.content.strip()
            
            return self._parse_section_response(ai_response, chunks)
            
        except Exception as e:
            print(f"    ⚠️ 섹션 AI 처리 실패: {str(e)}")
            return self._create_default_section_content(chunks, section_title)
    
    def _parse_section_response(self, ai_response: str, chunks: List[str]) -> Dict:
        """AI 응답을 구조화된 섹션 데이터로 변환합니다."""
        try:
            sections = ai_response.split('[')
            summary = ""
            keywords = []
            questions = []
            
            for section in sections:
                if section.startswith('요약]'):
                    summary = section.replace('요약]', '').strip()
                elif section.startswith('키워드]'):
                    keywords_text = section.replace('키워드]', '').strip()
                    keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
                elif section.startswith('예상질문]'):
                    questions_text = section.replace('예상질문]', '').strip()
                    questions = [q.strip() for q in questions_text.split('\n') if q.strip() and any(q.strip().startswith(str(i)) for i in range(1, 10))]
            
            return {
                "summary": summary or "요약을 생성할 수 없습니다.",
                "keywords": keywords or ["키워드", "추출", "실패"],
                "questions": questions or ["이 섹션의 주요 내용은 무엇인가요?"],
                "original_chunks": chunks,
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            print(f"    ⚠️ 응답 파싱 실패: {str(e)}")
            return self._create_default_section_content(chunks, "섹션")
    
    def _create_default_section_content(self, chunks: List[str], section_title: str) -> Dict:
        """기본 섹션 내용을 생성합니다."""
        return {
            "summary": f"이 섹션({section_title})에는 {len(chunks)}개의 텍스트 단위가 포함되어 있습니다.",
            "keywords": ["핵심", "내용", "학습", "이해", "정리"],
            "questions": [
                f"{section_title}의 주요 내용은 무엇인가요?",
                f"이 섹션에서 가장 중요한 개념은 무엇인가요?",
                f"실제로 어떻게 활용할 수 있을까요?"
            ],
            "original_chunks": chunks,
            "chunk_count": len(chunks)
        }
    
    def _save_curriculum(self, curriculum: Dict, file_name: str) -> str:
        """생성된 커리큘럼을 JSON 파일로 저장합니다."""
        try:
            json_path = f"{self.summaries_folder}/{file_name}_curriculum.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(curriculum, f, ensure_ascii=False, indent=2)
            
            print(f"  💾 커리큘럼 저장: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"  ⚠️ 커리큘럼 저장 실패: {str(e)}")
            return ""

# 사용 예시 함수
def create_curriculum_from_pdf(extracted_data: Dict) -> Dict:
    """
    추출된 PDF 데이터로부터 커리큘럼을 생성하는 간단한 함수입니다.
    
    Args:
        extracted_data: PDF에서 추출된 데이터
        
    Returns:
        생성된 커리큘럼
    """
    processor = AIProcessor()
    return processor.create_curriculum(extracted_data)

# 테스트용 메인 함수
if __name__ == "__main__":
    import sys
    import io
    
    # Windows 환경에서 UTF-8 출력 설정
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("🤖 AI Processor 모듈")
    print("💡 이 모듈은 main.py에서 import하여 사용됩니다.")
    print("🔑 OPENAI_API_KEY가 .env 파일에 설정되어 있는지 확인하세요.")