# PDF Learner 메인 서버 파일
# FastAPI를 사용한 웹 서버

import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.requests import Request
from dotenv import load_dotenv
from typing import List, Dict, Any
import shutil
from pathlib import Path
import json
from datetime import datetime

# Backend 모듈 import
import sys
sys.path.append("backend")
from pdf_processor import PDFProcessor
from ai_processor import AIProcessor
from chat_bot import ChatBot

# 환경변수 로드 (.env 파일에서 설정값들 읽어오기)
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="PDF Learner",
    description="AI를 활용한 PDF 학습 도우미",
    version="1.0.0"
)

# CORS 설정 (프론트엔드와 백엔드 연결을 위해 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경변수에서 설정값 가져오기
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
STATIC_FOLDER = os.getenv("STATIC_FOLDER", "static")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# 필요한 폴더들 자동 생성
def create_folders():
    """프로젝트에 필요한 폴더들을 자동으로 생성합니다."""
    folders = [
        UPLOAD_FOLDER,
        DATA_FOLDER,
        f"{DATA_FOLDER}/extracted",
        f"{DATA_FOLDER}/summaries", 
        f"{DATA_FOLDER}/vector_db",
        STATIC_FOLDER,
        "backend"
    ]
    
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)
    print("Required folders created successfully.")

# 전역 인스턴스
pdf_processor = None
ai_processor = None
chatbot = None

# 앱 시작 시 폴더 생성
@app.on_event("startup")
async def startup_event():
    global pdf_processor, ai_processor, chatbot
    create_folders()
    
    # 백엔드 프로세서 초기화
    try:
        pdf_processor = PDFProcessor(DATA_FOLDER)
        ai_processor = AIProcessor(DATA_FOLDER)
        chatbot = ChatBot(DATA_FOLDER)
        print("AI backend modules initialized successfully")
    except Exception as e:
        print(f"Warning: Error during AI module initialization: {e}")
        print("   Please check OPENAI_API_KEY in .env file.")
    
    print("PDF Learner server started!")

# 정적 파일 서빙 (CSS, JS, 이미지 등)
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend"), name="js")

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
                    <p>Upload folder: {UPLOAD_FOLDER}</p>
                    <p>Data folder: {DATA_FOLDER}</p>
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
        "upload_folder": UPLOAD_FOLDER,
        "data_folder": DATA_FOLDER
    }

@app.post("/upload")
async def upload_pdf(files: List[UploadFile] = File(...)):
    """PDF 파일들을 업로드하고 AI로 분석합니다."""
    try:
        uploaded_files = []
        
        for file in files:
            # 파일 확장자 확인
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"PDF 파일만 업로드 가능합니다: {file.filename}")
            
            # 파일 크기 확인 (메가바이트 변환)
            file_size_mb = len(await file.read()) / (1024 * 1024)
            await file.seek(0)  # 파일 포인터 처음으로 되돌리기
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                raise HTTPException(status_code=400, detail=f"파일 크기가 너무 큽니다: {file.filename} ({file_size_mb:.1f}MB)")
            
            # 파일 저장
            file_path = f"{UPLOAD_FOLDER}/{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_status = "uploaded"
            ai_processed = False
            
            # PDF 처리 및 AI 분석 (백그라운드에서 처리)
            if pdf_processor and ai_processor:
                try:
                    print(f"PDF processing started: {file.filename}")
                    # PDF 내용 추출
                    extracted_data = pdf_processor.extract_pdf_content(file_path)
                    
                    print(f"AI curriculum generation: {file.filename}")
                    # AI 커리큘럼 생성
                    curriculum = ai_processor.create_curriculum(extracted_data)
                    
                    # 채팅봇용 벡터 DB 생성
                    if chatbot:
                        print(f"Vector DB creation: {file.filename}")
                        chatbot.create_vector_database(extracted_data)
                    
                    print(f"{file.filename} AI processing completed")
                    file_status = "processed"
                    ai_processed = True
                except Exception as e:
                    print(f"Warning: {file.filename} AI processing failed: {e}")
                    file_status = "upload_only"
            else:
                print(f"Warning: AI module not initialized. Please check OPENAI_API_KEY in .env file.")
                file_status = "upload_only"
            
            uploaded_files.append({
                "filename": file.filename,
                "size_mb": round(file_size_mb, 2),
                "path": file_path,
                "status": file_status,
                "ai_processed": ai_processed
            })
        
        return {
            "message": f"{len(uploaded_files)}개의 PDF 파일이 성공적으로 업로드되었습니다!",
            "files": uploaded_files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 중 오류가 발생했습니다: {str(e)}")

@app.get("/files")
async def list_uploaded_files():
    """업로드된 파일 목록을 보여줍니다."""
    try:
        files = []
        upload_path = Path(UPLOAD_FOLDER)
        
        if upload_path.exists():
            for file_path in upload_path.glob("*.pdf"):
                file_size = file_path.stat().st_size / (1024 * 1024)  # MB로 변환
                upload_time = file_path.stat().st_mtime
                upload_date = datetime.fromtimestamp(upload_time).isoformat()
                
                # 파일명에서 확장자 제거하여 커리큘럼 파일 확인
                file_stem = file_path.stem
                curriculum_path = f"{DATA_FOLDER}/summaries/{file_stem}_curriculum.json"
                
                # 처리 상태 확인
                if os.path.exists(curriculum_path):
                    status = "completed"
                else:
                    status = "uploaded"
                
                files.append({
                    "filename": file_path.name,
                    "size_mb": round(file_size, 2),
                    "path": str(file_path),
                    "upload_date": upload_date,
                    "status": status
                })
        
        return {
            "total_files": len(files),
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 중 오류: {str(e)}")

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
        # 파일명에서 확장자 제거
        file_stem = filename.replace('.pdf', '')
        curriculum_path = f"{DATA_FOLDER}/summaries/{file_stem}_curriculum.json"
        
        # 커리큘럼 파일이 없으면 생성 시도
        if not os.path.exists(curriculum_path):
            print(f"Warning: Curriculum file not found: {curriculum_path}")
            
            # PDF 파일이 존재하는지 확인
            pdf_path = f"{UPLOAD_FOLDER}/{filename}"
            if not os.path.exists(pdf_path):
                raise HTTPException(status_code=404, detail=f"PDF 파일을 찾을 수 없습니다: {filename}")
            
            # AI 프로세서가 초기화되어 있는지 확인
            if not pdf_processor or not ai_processor:
                raise HTTPException(status_code=503, detail="AI 서비스가 초기화되지 않았습니다. .env 파일의 OPENAI_API_KEY를 확인해주세요.")
            
            try:
                print(f"PDF processing started: {filename}")
                # PDF 내용 추출
                extracted_data = pdf_processor.extract_pdf_content(pdf_path)
                
                print(f"AI curriculum generation started: {filename}")
                # AI 커리큘럼 생성
                curriculum = ai_processor.create_curriculum(extracted_data)
                
                # 채팅봇용 벡터 DB도 생성
                if chatbot:
                    print(f"Vector DB creation started: {filename}")
                    chatbot.create_vector_database(extracted_data)
                
                print(f"{filename} full processing completed")
                return curriculum
                
            except Exception as process_error:
                print(f"Error: AI processing failed: {process_error}")
                raise HTTPException(status_code=500, detail=f"AI 처리 중 오류: {str(process_error)}")
        
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
    # 환경변수에서 호스트와 포트 가져오기
    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"Server URL: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/docs")
    print(f"Debug Mode: {debug}")
    
    # 서버 시작
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug  # 개발 중에는 파일 변경 시 자동 재시작
    )