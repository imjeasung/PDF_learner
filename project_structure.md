# PDF Learner 프로젝트 폴더 구조

```
pdf-learner/
│
├── requirements.txt              # 라이브러리 목록 (이미 만듦)
├── .env                         # API 키 등 환경변수 (2단계에서 생성)
├── main.py                      # FastAPI 메인 서버 (3단계에서 생성)
│
├── backend/                     # 백엔드 관련 파일들
│   ├── __init__.py             # 폴더를 패키지로 만드는 파일
│   ├── pdf_processor.py        # PDF 내용 추출 (4단계)
│   ├── ai_processor.py         # AI 요약/목차 생성 (5단계) 
│   ├── database.py             # 데이터베이스 관련 (6단계)
│   └── chat_bot.py             # AI 질의응답 (7단계)
│
├── uploads/                     # 업로드된 PDF 파일 저장
│   └── (업로드된 PDF들이 여기 저장됨)
│
├── data/                        # 처리된 데이터 저장
│   ├── extracted/              # 추출된 텍스트/이미지
│   ├── summaries/              # AI 생성 요약들
│   └── vector_db/              # ChromaDB 벡터 저장소
│
├── frontend/                    # 프론트엔드 (8-9단계에서 생성)
│   ├── index.html              # 메인 페이지
│   ├── upload.html             # 파일 업로드 페이지
│   ├── study.html              # 학습 페이지
│   ├── css/
│   │   └── style.css           # 스타일 시트
│   └── js/
│       └── script.js           # JavaScript 파일
│
├── static/                      # 정적 파일 (이미지, CSS 등)
│   ├── css/
│   ├── js/
│   └── images/
│
└── README.md                    # 프로젝트 설명서 (마지막 단계)
```

## 폴더별 역할 설명

### 🗂️ 루트 폴더 (pdf-learner/)
- **requirements.txt**: 필요한 라이브러리 목록
- **.env**: OpenAI API 키 등 민감한 정보 저장
- **main.py**: FastAPI 서버의 시작점

### 🔧 backend/ 폴더
- **pdf_processor.py**: PDF에서 텍스트, 표, 이미지 추출
- **ai_processor.py**: AI를 이용한 요약, 목차 생성
- **database.py**: 데이터 저장/불러오기
- **chat_bot.py**: 질의응답 기능

### 📁 데이터 폴더들
- **uploads/**: 사용자가 업로드한 원본 PDF들
- **data/**: 처리된 데이터들 (추출된 내용, 요약 등)

### 🎨 frontend/ 폴더
- HTML, CSS, JavaScript 파일들
- 사용자가 보는 웹 페이지들

## 🚀 생성 순서
1. requirements.txt ✅ (완료)
2. .env (환경변수)
3. main.py (서버 시작)
4. backend/pdf_processor.py
5. backend/ai_processor.py
6. backend/database.py
7. backend/chat_bot.py
8. frontend 파일들
9. README.md

**"다음"**이라고 말씀하시면 2단계 파일부터 차례대로 만들어드리겠습니다!