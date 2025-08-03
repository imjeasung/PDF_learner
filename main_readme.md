# PDF Learner

> AI 기반 PDF 학습 도우미 웹 애플리케이션

## 📋 프로젝트 개요

PDF Learner는 사용자가 업로드한 PDF 문서를 AI가 분석하여 체계적인 학습 커리큘럼을 생성하고, 문서 내용 기반 질의응답을 제공하는 웹 애플리케이션입니다.

### 🎯 주요 기능

- **다중 PDF 파일 업로드**: 여러 PDF 파일을 한 번에 업로드
- **지능형 내용 추출**: 텍스트, 표, 이미지를 정확하게 추출
- **AI 커리큘럼 생성**: 목차별 요약, 핵심 키워드, 예상 질문 자동 생성
- **대화형 학습**: 문서 내용 기반 AI 채팅으로 질의응답
- **구조화된 학습**: 목차별로 체계적인 학습 진행

## 🛠 기술 스택

### Backend
- **Framework**: FastAPI (Python)
- **PDF Processing**: PyMuPDF, Camelot, Tabula-py
- **AI/LLM**: OpenAI API, LangChain
- **Database**: SQLite (초기), ChromaDB (Vector DB)

### Frontend
- **Framework**: React
- **Styling**: CSS Modules / Styled-components
- **State Management**: React Context / Redux Toolkit

### DevOps & Tools
- **Version Control**: Git
- **Package Management**: pip (Python), npm (Node.js)
- **Environment**: Python 3.9+, Node.js 18+

## 📁 프로젝트 구조

```
pdf-learner/
├── backend/          # Python/FastAPI 백엔드
├── frontend/         # React 프론트엔드
├── docs/            # 프로젝트 문서
├── data/            # 데이터 저장소
└── README.md        # 이 파일
```

## 🚀 개발 로드맵

### 1주차: 기획 및 기술 스택 선정
- [x] 요구사항 명세화
- [x] 기술 스택 선택
- [ ] 프로젝트 구조 설계
- [ ] 개발 환경 설정

### 2-4주차: 백엔드 핵심 기능 개발
- [ ] 파일 업로드 API
- [ ] PDF 내용 추출 모듈
- [ ] AI 커리큘럼 생성
- [ ] 질의응답 시스템 (RAG)

### 5-6주차: 프론트엔드 개발
- [ ] 파일 업로드 UI
- [ ] 학습 대시보드
- [ ] AI 채팅 인터페이스

### 7주차: 통합 및 테스트
- [ ] 프론트엔드-백엔드 연동
- [ ] 기능 테스트 및 버그 수정
- [ ] 성능 최적화

## 🔧 개발 환경 설정

### Prerequisites
- Python 3.9 이상
- Node.js 18 이상
- Git

### Backend 설정
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend 설정
```bash
cd frontend
npm install
npm start
```

### 환경 변수 설정
1. `backend/.env.example`을 복사하여 `backend/.env` 생성
2. OpenAI API 키 등 필요한 값들 설정

## 📖 문서

- [요구사항 명세서](docs/requirements.md)
- [API 명세서](docs/api_spec.md)
- [아키텍처 설계서](docs/architecture.md)
- [백엔드 문서](backend/README.md)
- [프론트엔드 문서](frontend/README.md)

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📧 연락처

프로젝트 문의: [이메일 주소]

Project Link: [https://github.com/username/pdf-learner](https://github.com/username/pdf-learner)

---

**개발 상태**: 🚧 진행 중 (1주차)
**최종 업데이트**: 2025년 8월