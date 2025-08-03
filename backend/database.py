# 데이터베이스 관리 모듈
# SQLite를 사용하여 PDF 파일 정보와 처리 결과를 저장합니다.

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 데이터베이스 설정
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pdf_learner.db")
Base = declarative_base()

class PDFDocument(Base):
    """PDF 문서 정보를 저장하는 테이블"""
    __tablename__ = "pdf_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_path = Column(String(500), nullable=False)
    file_size_mb = Column(Integer, nullable=False)  # 메가바이트 단위
    upload_date = Column(DateTime, default=datetime.utcnow)
    
    # 처리 상태
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="uploaded")  # uploaded, processing, completed, failed
    
    # PDF 메타데이터
    total_pages = Column(Integer, nullable=True)
    title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    
    # 파일 경로들
    extracted_data_path = Column(String(500), nullable=True)  # 추출된 데이터 JSON 경로
    curriculum_path = Column(String(500), nullable=True)      # 커리큘럼 JSON 경로
    
    # 통계 정보
    total_characters = Column(Integer, nullable=True)
    total_words = Column(Integer, nullable=True)
    total_images = Column(Integer, nullable=True)
    
    # 타임스탬프
    processed_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DatabaseManager:
    """데이터베이스 관리를 담당하는 클래스"""
    
    def __init__(self, database_url: str = None):
        """
        데이터베이스 매니저를 초기화합니다.
        
        Args:
            database_url: 데이터베이스 연결 URL
        """
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 테이블 생성
        self.create_tables()
        print(f"💾 데이터베이스 연결 완료: {self.database_url}")
    
    def create_tables(self):
        """데이터베이스 테이블을 생성합니다."""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("📋 데이터베이스 테이블 생성/확인 완료")
        except Exception as e:
            print(f"❌ 테이블 생성 실패: {str(e)}")
            raise
    
    def get_db_session(self) -> Session:
        """데이터베이스 세션을 생성합니다."""
        return self.SessionLocal()
    
    def add_pdf_document(self, filename: str, file_path: str, file_size_mb: float) -> int:
        """
        새로운 PDF 문서를 데이터베이스에 추가합니다.
        
        Args:
            filename: 파일명
            file_path: 파일 경로
            file_size_mb: 파일 크기 (MB)
            
        Returns:
            생성된 문서의 ID
        """
        try:
            with self.get_db_session() as db:
                document = PDFDocument(
                    filename=filename,
                    original_path=file_path,
                    file_size_mb=int(file_size_mb),
                    processing_status="uploaded"
                )
                
                db.add(document)
                db.commit()
                db.refresh(document)
                
                print(f"📄 문서 등록 완료: {filename} (ID: {document.id})")
                return document.id
                
        except Exception as e:
            print(f"❌ 문서 등록 실패: {str(e)}")
            raise
    
    def update_processing_status(self, document_id: int, status: str, error_message: str = None):
        """
        문서의 처리 상태를 업데이트합니다.
        
        Args:
            document_id: 문서 ID
            status: 새로운 상태 (processing, completed, failed)
            error_message: 오류 메시지 (실패 시)
        """
        try:
            with self.get_db_session() as db:
                document = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
                if document:
                    document.processing_status = status
                    document.last_updated = datetime.utcnow()
                    
                    if status == "completed":
                        document.is_processed = True
                        document.processed_date = datetime.utcnow()
                    
                    db.commit()
                    print(f"🔄 처리 상태 업데이트: ID {document_id} -> {status}")
                else:
                    print(f"⚠️ 문서를 찾을 수 없습니다: ID {document_id}")
                    
        except Exception as e:
            print(f"❌ 상태 업데이트 실패: {str(e)}")
    
    def update_pdf_metadata(self, document_id: int, extracted_data: Dict):
        """
        PDF 추출 데이터로 메타데이터를 업데이트합니다.
        
        Args:
            document_id: 문서 ID
            extracted_data: PDF에서 추출된 데이터
        """
        try:
            with self.get_db_session() as db:
                document = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
                if document:
                    # 기본 정보 업데이트
                    document.total_pages = extracted_data.get("total_pages", 0)
                    
                    # 메타데이터 업데이트
                    metadata = extracted_data.get("metadata", {})
                    document.title = metadata.get("title", "")[:500]  # 길이 제한
                    document.author = metadata.get("author", "")[:255]
                    
                    # 통계 정보 업데이트 (요약 정보가 있는 경우)
                    full_text = extracted_data.get("full_text", "")
                    document.total_characters = len(full_text)
                    document.total_words = len(full_text.split())
                    
                    # 이미지 개수 계산
                    total_images = 0
                    for page in extracted_data.get("pages", []):
                        total_images += len(page.get("images", []))
                    document.total_images = total_images
                    
                    # 파일 경로 설정
                    file_name = extracted_data.get("file_name", "")
                    document.extracted_data_path = f"data/extracted/{file_name}_extracted.json"
                    
                    db.commit()
                    print(f"📊 메타데이터 업데이트 완료: ID {document_id}")
                else:
                    print(f"⚠️ 문서를 찾을 수 없습니다: ID {document_id}")
                    
        except Exception as e:
            print(f"❌ 메타데이터 업데이트 실패: {str(e)}")
    
    def update_curriculum_path(self, document_id: int, curriculum_path: str):
        """
        커리큘럼 파일 경로를 업데이트합니다.
        
        Args:
            document_id: 문서 ID
            curriculum_path: 커리큘럼 JSON 파일 경로
        """
        try:
            with self.get_db_session() as db:
                document = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
                if document:
                    document.curriculum_path = curriculum_path
                    db.commit()
                    print(f"📚 커리큘럼 경로 업데이트: ID {document_id}")
                    
        except Exception as e:
            print(f"❌ 커리큘럼 경로 업데이트 실패: {str(e)}")
    
    def get_document_by_id(self, document_id: int) -> Optional[Dict]:
        """
        ID로 문서 정보를 조회합니다.
        
        Args:
            document_id: 문서 ID
            
        Returns:
            문서 정보 딕셔너리 또는 None
        """
        try:
            with self.get_db_session() as db:
                document = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
                if document:
                    return self._document_to_dict(document)
                return None
                
        except Exception as e:
            print(f"❌ 문서 조회 실패: {str(e)}")
            return None
    
    def get_document_by_filename(self, filename: str) -> Optional[Dict]:
        """
        파일명으로 문서 정보를 조회합니다.
        
        Args:
            filename: 파일명
            
        Returns:
            문서 정보 딕셔너리 또는 None
        """
        try:
            with self.get_db_session() as db:
                document = db.query(PDFDocument).filter(PDFDocument.filename == filename).first()
                if document:
                    return self._document_to_dict(document)
                return None
                
        except Exception as e:
            print(f"❌ 문서 조회 실패: {str(e)}")
            return None
    
    def get_all_documents(self, limit: int = 100) -> List[Dict]:
        """
        모든 문서 목록을 조회합니다.
        
        Args:
            limit: 최대 조회 개수
            
        Returns:
            문서 정보 리스트
        """
        try:
            with self.get_db_session() as db:
                documents = db.query(PDFDocument).order_by(PDFDocument.upload_date.desc()).limit(limit).all()
                return [self._document_to_dict(doc) for doc in documents]
                
        except Exception as e:
            print(f"❌ 문서 목록 조회 실패: {str(e)}")
            return []
    
    def get_processed_documents(self) -> List[Dict]:
        """
        처리 완료된 문서 목록을 조회합니다.
        
        Returns:
            처리 완료된 문서 정보 리스트
        """
        try:
            with self.get_db_session() as db:
                documents = db.query(PDFDocument).filter(
                    PDFDocument.is_processed == True,
                    PDFDocument.processing_status == "completed"
                ).order_by(PDFDocument.processed_date.desc()).all()
                
                return [self._document_to_dict(doc) for doc in documents]
                
        except Exception as e:
            print(f"❌ 처리된 문서 조회 실패: {str(e)}")
            return []
    
    def delete_document(self, document_id: int) -> bool:
        """
        문서를 데이터베이스에서 삭제합니다.
        
        Args:
            document_id: 삭제할 문서 ID
            
        Returns:
            삭제 성공 여부
        """
        try:
            with self.get_db_session() as db:
                document = db.query(PDFDocument).filter(PDFDocument.id == document_id).first()
                if document:
                    db.delete(document)
                    db.commit()
                    print(f"🗑️ 문서 삭제 완료: ID {document_id}")
                    return True
                else:
                    print(f"⚠️ 삭제할 문서를 찾을 수 없습니다: ID {document_id}")
                    return False
                    
        except Exception as e:
            print(f"❌ 문서 삭제 실패: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict:
        """
        데이터베이스 통계 정보를 조회합니다.
        
        Returns:
            통계 정보 딕셔너리
        """
        try:
            with self.get_db_session() as db:
                total_docs = db.query(PDFDocument).count()
                processed_docs = db.query(PDFDocument).filter(PDFDocument.is_processed == True).count()
                processing_docs = db.query(PDFDocument).filter(PDFDocument.processing_status == "processing").count()
                failed_docs = db.query(PDFDocument).filter(PDFDocument.processing_status == "failed").count()
                
                return {
                    "total_documents": total_docs,
                    "processed_documents": processed_docs,
                    "processing_documents": processing_docs,
                    "failed_documents": failed_docs,
                    "success_rate": round((processed_docs / total_docs * 100), 2) if total_docs > 0 else 0
                }
                
        except Exception as e:
            print(f"❌ 통계 조회 실패: {str(e)}")
            return {}
    
    def _document_to_dict(self, document: PDFDocument) -> Dict:
        """PDFDocument 객체를 딕셔너리로 변환합니다."""
        return {
            "id": document.id,
            "filename": document.filename,
            "original_path": document.original_path,
            "file_size_mb": document.file_size_mb,
            "upload_date": document.upload_date.isoformat() if document.upload_date else None,
            "is_processed": document.is_processed,
            "processing_status": document.processing_status,
            "total_pages": document.total_pages,
            "title": document.title,
            "author": document.author,
            "extracted_data_path": document.extracted_data_path,
            "curriculum_path": document.curriculum_path,
            "total_characters": document.total_characters,
            "total_words": document.total_words,
            "total_images": document.total_images,
            "processed_date": document.processed_date.isoformat() if document.processed_date else None,
            "last_updated": document.last_updated.isoformat() if document.last_updated else None
        }

# 전역 데이터베이스 매니저 인스턴스
db_manager = None

def get_database_manager() -> DatabaseManager:
    """전역 데이터베이스 매니저 인스턴스를 반환합니다."""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

# 편의 함수들
def add_document(filename: str, file_path: str, file_size_mb: float) -> int:
    """문서 추가 편의 함수"""
    return get_database_manager().add_document(filename, file_path, file_size_mb)

def get_document(document_id: int) -> Optional[Dict]:
    """문서 조회 편의 함수"""
    return get_database_manager().get_document_by_id(document_id)

def update_status(document_id: int, status: str):
    """상태 업데이트 편의 함수"""
    get_database_manager().update_processing_status(document_id, status)

# 테스트용 메인 함수
if __name__ == "__main__":
    print("🧪 데이터베이스 테스트 시작...")
    
    try:
        # 데이터베이스 매니저 생성
        db = DatabaseManager()
        
        # 테스트 문서 추가
        doc_id = db.add_pdf_document("test.pdf", "uploads/test.pdf", 1.5)
        print(f"✅ 테스트 문서 추가됨: ID {doc_id}")
        
        # 문서 조회
        document = db.get_document_by_id(doc_id)
        if document:
            print(f"✅ 문서 조회 성공: {document['filename']}")
        
        # 통계 조회
        stats = db.get_statistics()
        print(f"📊 데이터베이스 통계: {stats}")
        
        # 테스트 문서 삭제
        db.delete_document(doc_id)
        print("✅ 테스트 문서 삭제됨")
        
        print("🎉 데이터베이스 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {str(e)}")