# PDF Learner 메인 서버 파일
# FastAPI를 사용한 웹 서버

import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.requests import Request
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import List, Dict, Any
import shutil
from pathlib import Path
import json
from datetime import datetime
import asyncio
import threading
import logging
import sys
from urllib.parse import unquote

# Backend 모듈 import
import sys
sys.path.append("backend")
from pdf_processor import PDFProcessor
from ai_processor import AIProcessor
from chat_bot import ChatBot
from database import DatabaseManager

# 새로운 모듈들 import
from backend.config import settings, validate_settings, print_settings
from backend.constants import *
from backend.utils import (
    validate_file_basic, validate_pdf_content, sanitize_filename,
    ensure_directory, get_safe_path, create_success_response, 
    create_error_response, log_operation, get_file_size_mb
)

# 환경변수 로드 및 검증
load_dotenv()
validate_settings()  # 설정 검증 수행

# Windows 환경에서 UTF-8 출력 설정
import io
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass  # 이미 설정된 경우 무시

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 전역 변수 선언
pdf_processor = None
ai_processor = None
chatbot = None
db_manager = None

# 파일 처리 상태 추적
file_processing_status = {}

# 필요한 폴더들 자동 생성
def create_folders():
    """프로젝트에 필요한 폴더들을 자동으로 생성합니다."""
    folders = settings.get_folder_paths()
    
    success_count = 0
    for folder in folders:
        if ensure_directory(folder):
            success_count += 1
    
    log_operation("Folder creation", {"created": success_count, "total": len(folders)})
    return success_count == len(folders)


# Lifespan 이벤트 처리 (새로운 FastAPI 방식)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup 이벤트
    global pdf_processor, ai_processor, chatbot, db_manager
    
    # 설정 정보 출력
    if settings.DEBUG:
        print_settings()
    
    # 폴더 생성
    if create_folders():
        log_operation("Startup folders", success=True)
    else:
        log_operation("Startup folders", success=False)
    
    # 데이터베이스 초기화
    try:
        db_manager = DatabaseManager(settings.DATABASE_URL)
        log_operation("Database initialization", success=True)
    except Exception as e:
        log_operation("Database initialization", {"error": str(e)}, success=False)
    
    # 백엔드 프로세서 초기화
    try:
        pdf_processor = PDFProcessor(settings.DATA_FOLDER)
        ai_processor = AIProcessor(settings.DATA_FOLDER)
        chatbot = ChatBot(settings.DATA_FOLDER)
        log_operation("AI modules initialization", success=True)
    except Exception as e:
        log_operation("AI modules initialization", {"error": str(e)}, success=False)
        logger.warning(f"   Please check {ERROR_MESSAGES['OPENAI_KEY_MISSING']}")
    
    log_operation("PDF Learner server startup", {"environment": "production" if settings.IS_PRODUCTION else "development"}, success=True)
    
    yield  # 여기서 애플리케이션이 실행됨
    
    # Shutdown 이벤트 (필요한 경우 정리 작업 추가 가능)
    log_operation("PDF Learner server shutdown", success=True)

# FastAPI 앱 생성
app = FastAPI(
    title="PDF Learner",
    description="AI를 활용한 PDF 학습 도우미",
    version=APP_VERSION,
    lifespan=lifespan
)

# CORS 설정 (프론트엔드와 백엔드 연결을 위해 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # config에서 관리되는 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (CSS, JS, 이미지 등)
# 디렉토리가 존재하는 경우에만 마운트
for mount_path, directory in STATIC_PATHS.items():
    if os.path.exists(directory):
        if mount_path == 'CSS':
            app.mount("/css", StaticFiles(directory=directory), name="css")
        elif mount_path == 'JS':
            app.mount("/js", StaticFiles(directory=directory), name="js")
        elif mount_path == 'UPLOADS':
            # uploads는 별도 처리
            pass

if os.path.exists(settings.STATIC_FOLDER):
    app.mount("/static", StaticFiles(directory=settings.STATIC_FOLDER), name="static")

# 루트 경로의 정적 파일들을 위한 추가 마운트
from fastapi.responses import FileResponse
import os

# =================== API 엔드포인트들 ===================

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def read_root():
    """메인 페이지를 보여줍니다."""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"""
        <html>
            <head>
                <title>PDF Learner</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    h1 {{ color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .btn {{ background: #007bff; color: white; padding: 10px 20px; 
                           text-decoration: none; border-radius: 5px; margin: 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📚 PDF Learner</h1>
                    <p>AI를 활용한 PDF 학습 도우미입니다.</p>
                    <p>frontend/index.html 파일을 찾을 수 없습니다.</p>
                    
                    <div>
                        <a href="/docs" class="btn">API 문서 보기</a>
                    </div>
                    
                    <h3>📋 서버 상태</h3>
                    <p>Server is running normally!</p>
                    <p>Upload folder: {settings.UPLOAD_FOLDER}</p>
                    <p>Data folder: {settings.DATA_FOLDER}</p>
                </div>
            </body>
        </html>
        """

@app.get("/upload.html", response_class=HTMLResponse)
async def upload_page():
    """업로드 페이지를 보여줍니다."""
    try:
        with open("frontend/upload.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("upload.html 파일을 찾을 수 없습니다.", status_code=404)

@app.get("/study.html", response_class=HTMLResponse)
async def study_page():
    """학습 페이지를 보여줍니다."""
    try:
        with open("frontend/study.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("study.html 파일을 찾을 수 없습니다.", status_code=404)

@app.get("/health")
async def health_check():
    """서버 상태를 확인합니다."""
    return {
        "status": "healthy",
        "message": "PDF Learner 서버가 정상 작동 중입니다!",
        "upload_folder": settings.UPLOAD_FOLDER,
        "data_folder": settings.DATA_FOLDER
    }

@app.get("/api/models")
async def get_available_models():
    """사용 가능한 AI 모델 목록을 반환합니다."""
    try:
        from backend.ai_providers import get_ai_manager
        
        manager = get_ai_manager()
        models = {
            "text_models": settings.SUPPORTED_TEXT_MODELS,
            "embedding_models": settings.SUPPORTED_EMBEDDING_MODELS,
            "current_provider": manager.current_provider,
            "providers": list(settings.AI_PROVIDERS_CONFIG.keys())
        }
        
        return create_success_response(
            message="모델 목록 조회 성공",
            data=models
        )
        
    except Exception as e:
        logger.error(f"❌ 모델 목록 조회 실패: {str(e)}")
        return create_error_response(
            message=f"모델 목록 조회 실패: {str(e)}",
            status_code=500
        )

@app.get("/api/settings")
async def get_current_settings():
    """현재 AI 설정을 반환합니다."""
    try:
        from backend.ai_providers import get_ai_manager
        
        manager = get_ai_manager()
        current_settings = {
            "current_provider": manager.current_provider,
            "text_model": settings.AI_PROVIDERS_CONFIG.get(manager.current_provider, {}).get("default_model"),
            "embedding_model": settings.AI_PROVIDERS_CONFIG.get(manager.current_provider, {}).get("embedding_model"),
            "max_tokens": os.getenv("MAX_TOKENS", "1000"),
            "temperature": os.getenv("TEMPERATURE", "0.7"),
            "enable_multi_provider": settings.ENABLE_MULTI_PROVIDER
        }
        
        return create_success_response(
            message="설정 조회 성공",
            data=current_settings
        )
        
    except Exception as e:
        logger.error(f"❌ 설정 조회 실패: {str(e)}")
        return create_error_response(
            message=f"설정 조회 실패: {str(e)}",
            status_code=500
        )

@app.post("/api/settings")
async def update_settings(request: Request):
    """AI 설정을 업데이트합니다."""
    try:
        data = await request.json()
        
        # 환경변수 업데이트 (임시적, 재시작 시 초기화됨)
        if "text_model" in data:
            os.environ["OPENAI_MODEL"] = data["text_model"]
        if "embedding_model" in data:
            os.environ["OPENAI_EMBEDDING_MODEL"] = data["embedding_model"]
        if "max_tokens" in data:
            os.environ["MAX_TOKENS"] = str(data["max_tokens"])
        if "temperature" in data:
            os.environ["TEMPERATURE"] = str(data["temperature"])
        
        # AI 모듈들에 새 설정 반영
        global ai_processor, chatbot
        
        # AI Processor 재초기화
        ai_processor = AIProcessor()
        chatbot = ChatBot() if chatbot else None
        
        logger.info(f"✅ AI 설정 업데이트 완료: {data}")
        
        return create_success_response(
            message="설정이 성공적으로 업데이트되었습니다",
            data=data
        )
        
    except Exception as e:
        logger.error(f"❌ 설정 업데이트 실패: {str(e)}")
        return create_error_response(
            message=f"설정 업데이트 실패: {str(e)}",
            status_code=500
        )

def process_pdf_background(file_path: str, filename: str, document_id: int = None):
    """백그라운드에서 PDF를 처리하는 통합 함수"""
    try:
        # 처리 상태를 'processing'으로 변경
        file_processing_status[filename] = {
            "status": "processing",
            "progress": 50,
            "message": "AI 분석 중...",
            "document_id": document_id
        }
        
        # 데이터베이스 상태 업데이트
        if db_manager and document_id:
            db_manager.update_processing_status(document_id, "processing")
        
        logger.info(f"🚀 Background PDF processing started: {filename}")
        
        # PDF 내용 추출
        logger.info(f"📄 PDF 내용 추출 시작: {filename}")
        extracted_data = pdf_processor.extract_pdf_content(file_path)
        
        # 데이터베이스에 메타데이터 업데이트
        if db_manager and document_id:
            db_manager.update_pdf_metadata(document_id, extracted_data)
        
        # AI 커리큘럼 생성
        logger.info(f"🤖 AI curriculum generation started: {filename}")
        curriculum = ai_processor.create_curriculum(extracted_data)
        
        # 채팅봇용 벡터 DB 생성
        if chatbot:
            logger.info(f"📊 Vector DB creation started: {filename}")
            chatbot.create_vector_database(extracted_data)
        
        # 처리 완료
        file_processing_status[filename] = {
            "status": "completed",
            "progress": 100,
            "message": "AI 분석 완료!",
            "document_id": document_id
        }
        
        # 데이터베이스 상태 업데이트
        if db_manager and document_id:
            db_manager.update_processing_status(document_id, "completed")
        
        logger.info(f"🎉 {filename} Background AI processing completed successfully!")
        
    except Exception as e:
        error_msg = f"AI 처리 실패: {str(e)}"
        file_processing_status[filename] = {
            "status": "failed",
            "progress": 0,
            "message": error_msg,
            "document_id": document_id
        }
        
        # 데이터베이스 상태 업데이트
        if db_manager and document_id:
            db_manager.update_processing_status(document_id, "failed", error_msg)
        
        logger.error(f"❌ {filename} Background AI processing failed: {e}")

@app.post("/upload")
async def upload_pdf(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """PDF 파일들을 업로드하고 백그라운드에서 AI로 분석합니다."""
    try:
        uploaded_files = []
        
        for file in files:
            # 1. 파일 정보 추출
            if not file.filename:
                raise HTTPException(status_code=HTTP_STATUS['BAD_REQUEST'], 
                                  detail="파일명이 비어있습니다.")
            
            # 파일 내용 읽기
            file_content = await file.read()
            await file.seek(0)
            file_size_bytes = len(file_content)
            file_size_mb = get_file_size_mb(file_size_bytes)
            
            # 2. 기본 파일 검증
            is_valid, error_msg = validate_file_basic(file.filename, file_size_bytes)
            if not is_valid:
                raise HTTPException(status_code=HTTP_STATUS['BAD_REQUEST'], detail=error_msg)
            
            # 3. PDF 내용 검증
            is_pdf_valid, pdf_error = validate_pdf_content(file_content)
            if not is_pdf_valid:
                raise HTTPException(status_code=HTTP_STATUS['BAD_REQUEST'], detail=pdf_error)
            
            # 4. 안전한 파일명 생성
            safe_filename = sanitize_filename(file.filename)
            safe_file_path = get_safe_path(settings.UPLOAD_FOLDER, safe_filename)
            
            # 5. 파일 저장
            try:
                with open(safe_file_path, "wb") as buffer:
                    buffer.write(file_content)
                log_operation("File upload", {"filename": safe_filename, "size_mb": file_size_mb})
            except Exception as e:
                raise HTTPException(status_code=HTTP_STATUS['INTERNAL_ERROR'], 
                                  detail=f"파일 저장 실패: {str(e)}")
            
            # 6. 데이터베이스에 문서 정보 저장
            document_id = None
            if db_manager:
                try:
                    document_id = db_manager.add_pdf_document(safe_filename, safe_file_path, file_size_mb)
                    log_operation("Database record", {"filename": safe_filename, "doc_id": document_id})
                except Exception as e:
                    log_operation("Database record", {"filename": safe_filename, "error": str(e)}, success=False)
            
            # 7. 초기 상태 설정
            file_processing_status[safe_filename] = {
                "status": PROCESSING_STATUS['UPLOADED'],
                "progress": 0,
                "message": "업로드 완료, AI 처리 대기 중...",
                "document_id": document_id
            }
            
            # 8. 백그라운드 AI 처리 시작
            if pdf_processor and ai_processor:
                background_tasks.add_task(process_pdf_background, safe_file_path, safe_filename, document_id)
                file_status = PROCESSING_STATUS['PROCESSING']
                log_operation("AI processing started", {"filename": safe_filename})
            else:
                file_status = "upload_only"
                file_processing_status[safe_filename].update({
                    "status": "upload_only",
                    "progress": 100,
                    "message": ERROR_MESSAGES['AI_NOT_INITIALIZED']
                })
                log_operation("AI processing skipped", {"filename": safe_filename, "reason": "AI not initialized"}, success=False)
            
            # 9. 업로드 결과 추가
            uploaded_files.append({
                "filename": safe_filename,
                "original_filename": file.filename,
                "size_mb": file_size_mb,
                "path": safe_file_path,
                "status": file_status,
                "processing_status": file_processing_status[safe_filename]
            })
        
        # 10. 성공 응답 반환 (기존 형식 유지)
        return {
            "message": f"{len(uploaded_files)}개의 PDF 파일이 성공적으로 업로드되었습니다! AI 분석이 백그라운드에서 진행됩니다.",
            "files": uploaded_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_operation("File upload", {"error": str(e)}, success=False)
        raise HTTPException(status_code=HTTP_STATUS['INTERNAL_ERROR'], 
                          detail=f"업로드 중 오류가 발생했습니다: {str(e)}")

@app.get("/files")
async def list_uploaded_files():
    """업로드된 파일 목록을 보여줍니다."""
    try:
        files = []
        upload_path = Path(settings.UPLOAD_FOLDER)
        
        if upload_path.exists():
            for file_path in upload_path.glob("*.pdf"):
                file_size_bytes = file_path.stat().st_size
                file_size_mb = get_file_size_mb(file_size_bytes)
                upload_time = file_path.stat().st_mtime
                upload_date = datetime.fromtimestamp(upload_time).isoformat()
                
                # 파일명에서 확장자 제거하여 커리큘럼 파일 확인
                file_stem = file_path.stem
                curriculum_path = f"{settings.SUMMARIES_FOLDER}/{file_stem}_curriculum.json"
                
                # 처리 상태 확인 (메모리 상태와 파일 상태 모두 확인)
                filename = file_path.name
                if filename in file_processing_status:
                    # 메모리에 처리 상태가 있는 경우
                    processing_info = file_processing_status[filename]
                    status = processing_info["status"]
                    processing_status = processing_info
                elif os.path.exists(curriculum_path):
                    # 커리큘럼 파일이 존재하는 경우 (이전에 처리 완료됨)
                    status = PROCESSING_STATUS['COMPLETED']
                    processing_status = {
                        "status": PROCESSING_STATUS['COMPLETED'],
                        "progress": 100,
                        "message": "AI 분석 완료!"
                    }
                else:
                    # 아직 처리되지 않은 경우
                    status = PROCESSING_STATUS['UPLOADED']
                    processing_status = {
                        "status": PROCESSING_STATUS['UPLOADED'],
                        "progress": 0,
                        "message": "AI 처리 대기 중..."
                    }
                
                files.append({
                    "filename": filename,
                    "size_mb": file_size_mb,
                    "path": str(file_path),
                    "upload_date": upload_date,
                    "status": status,
                    "processing_status": processing_status
                })
        
        return {
            "total_files": len(files),
            "files": files
        }
        
    except Exception as e:
        log_operation("File list retrieval", {"error": str(e)}, success=False)
        raise HTTPException(status_code=HTTP_STATUS['INTERNAL_ERROR'], 
                          detail=f"파일 목록 조회 중 오류: {str(e)}")

@app.get("/processing-status/{filename}")
async def get_processing_status(filename: str):
    """특정 파일의 처리 상태를 확인합니다."""
    try:
        if filename in file_processing_status:
            return {
                "filename": filename,
                "processing_status": file_processing_status[filename]
            }
        else:
            # 파일 상태가 메모리에 없는 경우, 커리큘럼 파일 확인
            file_stem = filename.replace('.pdf', '')
            curriculum_path = f"{settings.SUMMARIES_FOLDER}/{file_stem}_curriculum.json"
            
            if os.path.exists(curriculum_path):
                return {
                    "filename": filename,
                    "processing_status": {
                        "status": "completed",
                        "progress": 100,
                        "message": "AI 분석 완료!"
                    }
                }
            else:
                return {
                    "filename": filename,
                    "processing_status": {
                        "status": "uploaded",
                        "progress": 0,
                        "message": "AI 처리 대기 중..."
                    }
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 상태 확인 중 오류: {str(e)}")

@app.post("/chat")
async def chat_with_document(request: Request):
    """문서 기반 AI 채팅"""
    try:
        data = await request.json()
        question = data.get("question", "")
        document = data.get("document", "")
        
        if not question:
            raise HTTPException(status_code=400, detail="질문이 필요합니다.")
        
        if not document:
            raise HTTPException(status_code=400, detail="문서명이 필요합니다.")
        
        if not chatbot:
            raise HTTPException(status_code=503, detail="AI 서비스가 초기화되지 않았습니다.")
        
        # AI 답변 생성
        result = chatbot.answer_question(question, document)
        
        return {
            "question": question,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0.0),
            "document": document
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류: {str(e)}")

@app.get("/curriculum/{filename}")
async def get_curriculum(filename: str):
    """특정 문서의 커리큘럼을 가져옵니다."""
    try:
        # URL 디코딩 및 파일명 정리
        decoded_filename = unquote(filename)
        safe_filename = sanitize_filename(decoded_filename)
        
        log_operation("Curriculum request", {
            "original": filename,
            "decoded": decoded_filename, 
            "safe": safe_filename
        })
        
        # 파일명에서 확장자 제거
        file_stem = safe_filename.replace('.pdf', '')
        curriculum_path = f"{settings.SUMMARIES_FOLDER}/{file_stem}_curriculum.json"
        
        # 커리큘럼 파일이 없으면 생성 시도
        if not os.path.exists(curriculum_path):
            log_operation("Curriculum file not found", {"path": curriculum_path})
            
            # PDF 파일이 존재하는지 확인 (안전한 경로 사용)
            try:
                pdf_path = get_safe_path(settings.UPLOAD_FOLDER, safe_filename)
                if not os.path.exists(pdf_path):
                    raise HTTPException(status_code=HTTP_STATUS['NOT_FOUND'], 
                                      detail=f"PDF 파일을 찾을 수 없습니다: {safe_filename}")
            except ValueError as e:
                raise HTTPException(status_code=HTTP_STATUS['BAD_REQUEST'], 
                                  detail=f"잘못된 파일 경로: {str(e)}")
            
            # AI 프로세서가 초기화되어 있는지 확인
            if not pdf_processor or not ai_processor:
                raise HTTPException(status_code=503, detail="AI 서비스가 초기화되지 않았습니다. .env 파일의 OPENAI_API_KEY를 확인해주세요.")
            
            try:
                log_operation("PDF processing started", {"filename": safe_filename})
                # PDF 내용 추출
                extracted_data = pdf_processor.extract_pdf_content(pdf_path)
                
                log_operation("AI curriculum generation started", {"filename": safe_filename})
                # AI 커리큘럼 생성
                curriculum = ai_processor.create_curriculum(extracted_data)
                
                # 채팅봇용 벡터 DB도 생성
                if chatbot:
                    log_operation("Vector DB creation started", {"filename": safe_filename})
                    chatbot.create_vector_database(extracted_data)
                
                log_operation("Full processing completed", {"filename": safe_filename})
                return curriculum
                
            except Exception as process_error:
                log_operation("AI processing failed", {"filename": safe_filename, "error": str(process_error)}, success=False)
                raise HTTPException(status_code=HTTP_STATUS['INTERNAL_ERROR'], 
                                  detail=f"AI 처리 중 오류: {str(process_error)}")
        
        # 커리큘럼 파일이 존재하면 로드
        with open(curriculum_path, 'r', encoding='utf-8') as f:
            curriculum = json.load(f)
        
        return curriculum
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: Curriculum query failed: {e}")
        raise HTTPException(status_code=500, detail=f"커리큘럼 조회 중 오류: {str(e)}")

@app.get("/documents")
async def get_available_documents():
    """채팅 가능한 문서 목록을 반환합니다."""
    try:
        if not chatbot:
            return {"documents": []}
        
        available_docs = chatbot.get_available_documents()
        return {"documents": available_docs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 중 오류: {str(e)}")

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    """업로드된 파일과 관련 데이터를 모두 삭제합니다."""
    try:
        # 안전한 URL 디코딩 및 파일명 정리
        decoded_filename = unquote(filename)
        safe_filename = sanitize_filename(decoded_filename)
        
        log_operation("Delete request", {
            "original": filename,
            "decoded": decoded_filename,
            "safe": safe_filename
        })
        
        # 삭제할 파일 경로들
        upload_file_path = get_safe_path(settings.UPLOAD_FOLDER, safe_filename)
        file_stem = safe_filename.replace('.pdf', '')
        
        # 관련 파일 경로들
        extracted_data_path = f"{settings.EXTRACTED_FOLDER}/{file_stem}_extracted.json"
        curriculum_path = f"{settings.SUMMARIES_FOLDER}/{file_stem}_curriculum.json"
        vector_db_path = f"{settings.VECTOR_DB_FOLDER}/{file_stem}"
        
        deleted_files = []
        
        # 1. 업로드된 원본 PDF 파일 삭제
        if os.path.exists(upload_file_path):
            os.remove(upload_file_path)
            deleted_files.append("원본 PDF 파일")
            logger.info(f"📄 원본 파일 삭제: {upload_file_path}")
        
        # 2. 추출된 데이터 JSON 파일 삭제
        if os.path.exists(extracted_data_path):
            os.remove(extracted_data_path)
            deleted_files.append("추출된 데이터")
            logger.info(f"📊 추출 데이터 삭제: {extracted_data_path}")
        
        # 3. 커리큘럼 JSON 파일 삭제
        if os.path.exists(curriculum_path):
            os.remove(curriculum_path)
            deleted_files.append("AI 커리큘럼")
            logger.info(f"📚 커리큘럼 삭제: {curriculum_path}")
        
        # 4. 벡터 데이터베이스 폴더 삭제 (채팅봇 캐시)
        if os.path.exists(vector_db_path):
            shutil.rmtree(vector_db_path)
            deleted_files.append("벡터 데이터베이스")
            logger.info(f"🗃️ 벡터 DB 삭제: {vector_db_path}")
        
        # 5. 메모리에서 처리 상태 제거
        if filename in file_processing_status:
            del file_processing_status[filename]
            deleted_files.append("처리 상태 캐시")
            logger.info(f"🧹 메모리 캐시 정리: {filename}")
        
        # 6. 채팅봇 메모리에서 문서 제거 (있는 경우)
        if chatbot:
            try:
                # 채팅봇의 문서 캐시 정리
                if hasattr(chatbot, 'remove_document'):
                    chatbot.remove_document(file_stem)
                    deleted_files.append("채팅봇 캐시")
                    logger.info(f"🤖 채팅봇 캐시 정리: {file_stem}")
            except Exception as chatbot_error:
                logger.warning(f"⚠️ 채팅봇 캐시 정리 실패: {chatbot_error}")
        
        if not deleted_files:
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {filename}")
        
        logger.info(f"✅ 파일 삭제 완료: {filename} (삭제된 항목: {', '.join(deleted_files)})")
        
        return {
            "message": f"'{filename}' 파일과 관련 데이터가 모두 삭제되었습니다.",
            "deleted_items": deleted_files,
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 파일 삭제 실패: {filename} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 삭제 중 오류가 발생했습니다: {str(e)}")

@app.get("/uploads/{filename}")
async def download_file(filename: str):
    """업로드된 파일을 다운로드합니다."""
    try:
        # 파일명 디코딩
        filename = filename.replace("%20", " ")
        file_path = f"{settings.UPLOAD_FOLDER}/{filename}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {filename}")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 파일 다운로드 실패: {filename} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")

# 정적 파일 직접 서빙
@app.get("/style.css")
async def get_style_css():
    """메인 CSS 파일을 서빙합니다."""
    css_path = "frontend/css/style.css"
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS 파일을 찾을 수 없습니다.")

@app.get("/script.js")
async def get_script_js():
    """메인 JavaScript 파일을 서빙합니다."""
    js_path = "frontend/script.js"
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="text/javascript")
    raise HTTPException(status_code=404, detail="JavaScript 파일을 찾을 수 없습니다.")

@app.get("/favicon.ico")
async def get_favicon():
    """파비콘을 서빙합니다."""
    favicon_path = "frontend/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    # 파비콘이 없으면 빈 응답 반환 (404 대신)
    return FileResponse("static/.gitkeep", media_type="image/x-icon") if os.path.exists("static/.gitkeep") else ""

# =================== 서버 실행 ===================

if __name__ == "__main__":
    # 환경변수에서 호스트와 포트 가져오기 (Koyeb 배포용)
    host = os.getenv("HOST", "0.0.0.0")  # Koyeb에서는 0.0.0.0이 필요
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"  # 프로덕션에서는 기본적으로 False
    
    # Koyeb 환경에서는 reload 비활성화
    is_production = os.getenv("KOYEB_PUBLIC_DOMAIN") is not None
    
    print(f"🚀 Starting PDF Learner Server...")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🛠️ Debug Mode: {debug}")
    print(f"📊 API Docs: http://localhost:{port}/docs")
    print(f"🌐 Server URL: http://0.0.0.0:{port}")
    
    # 서버 시작
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug and not is_production,  # 프로덕션에서는 reload 비활성화
        access_log=True,
        log_level="info" if not debug else "debug"
    )
