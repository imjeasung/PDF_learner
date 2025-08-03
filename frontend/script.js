// PDF Learner JavaScript 파일
// 모든 인터랙티브 기능과 API 통신을 담당합니다

// ===== 전역 변수 및 설정 =====
const API_BASE_URL = window.location.origin;
let currentDocuments = [];
let isUploading = false;

// ===== 유틸리티 함수들 =====

/**
 * API 호출을 위한 기본 fetch 함수
 */
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || `HTTP error! status: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error(`API call failed for ${endpoint}:`, error);
        throw error;
    }
}

/**
 * 파일 크기를 읽기 쉬운 형태로 변환
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 날짜를 읽기 쉬운 형태로 변환
 */
function formatDate(dateString) {
    if (!dateString) return '알 수 없음';
    
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;
    
    return date.toLocaleDateString('ko-KR');
}

/**
 * 성공/오류 메시지 표시
 */
function showMessage(message, type = 'info') {
    // 기존 메시지 제거
    const existingMessage = document.querySelector('.message-popup');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 새 메시지 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-popup message-${type}`;
    messageDiv.innerHTML = `
        <div class="message-content">
            <i class="fas fa-${getMessageIcon(type)}"></i>
            <span>${message}</span>
            <button class="message-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // 메시지 스타일
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        animation: slideInRight 0.3s ease;
        max-width: 400px;
        background: ${getMessageColor(type)};
    `;
    
    document.body.appendChild(messageDiv);
    
    // 5초 후 자동 제거
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => messageDiv.remove(), 300);
        }
    }, 5000);
}

function getMessageIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function getMessageColor(type) {
    const colors = {
        success: 'linear-gradient(45deg, #2ecc71, #27ae60)',
        error: 'linear-gradient(45deg, #e74c3c, #c0392b)',
        warning: 'linear-gradient(45deg, #f39c12, #e67e22)',
        info: 'linear-gradient(45deg, #3498db, #2980b9)'
    };
    return colors[type] || colors.info;
}

/**
 * 로딩 스피너 표시/숨김
 */
function showLoading(element, show = true) {
    if (show) {
        element.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <span>처리 중...</span>
            </div>
        `;
        element.style.opacity = '0.7';
    } else {
        element.style.opacity = '1';
    }
}

// ===== 파일 업로드 관련 함수들 =====

/**
 * 파일 유효성 검사
 */
function validateFile(file) {
    const maxSize = 50 * 1024 * 1024; // 50MB
    const allowedTypes = ['application/pdf'];
    
    if (!allowedTypes.includes(file.type)) {
        throw new Error('PDF 파일만 업로드 가능합니다.');
    }
    
    if (file.size > maxSize) {
        throw new Error('파일 크기는 50MB를 초과할 수 없습니다.');
    }
    
    return true;
}

/**
 * 단일 파일 업로드
 */
async function uploadSingleFile(file) {
    validateFile(file);
    
    const formData = new FormData();
    formData.append('files', file);
    
    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '업로드에 실패했습니다.');
    }
    
    return response.json();
}

/**
 * 여러 파일 업로드
 */
async function uploadMultipleFiles(files) {
    const results = [];
    const errors = [];
    
    for (let i = 0; i < files.length; i++) {
        try {
            const result = await uploadSingleFile(files[i]);
            results.push(result);
            showMessage(`${files[i].name} 업로드 완료`, 'success');
        } catch (error) {
            errors.push({ file: files[i].name, error: error.message });
            showMessage(`${files[i].name} 업로드 실패: ${error.message}`, 'error');
        }
    }
    
    return { results, errors };
}

// ===== 문서 관리 함수들 =====

/**
 * 문서 목록 가져오기
 */
async function fetchDocuments() {
    try {
        const data = await apiCall('/files');
        currentDocuments = data.files || [];
        return data;
    } catch (error) {
        showMessage('문서 목록을 불러오는데 실패했습니다.', 'error');
        return { files: [], total_files: 0 };
    }
}

/**
 * 서버 상태 확인
 */
async function checkServerHealth() {
    try {
        const data = await apiCall('/health');
        return data;
    } catch (error) {
        console.error('Server health check failed:', error);
        return { status: 'error', message: 'Server connection failed' };
    }
}

/**
 * 문서 처리 상태 확인
 */
async function checkProcessingStatus(filename) {
    try {
        // 실제 API가 구현되면 해당 엔드포인트 사용
        // const data = await apiCall(`/status/${filename}`);
        // 현재는 더미 데이터 반환
        return { status: 'completed', progress: 100 };
    } catch (error) {
        console.error('Processing status check failed:', error);
        return { status: 'error', progress: 0 };
    }
}

// ===== 문서 표시 함수들 =====

/**
 * 문서 카드 HTML 생성
 */
function createDocumentCard(doc) {
    const uploadDate = formatDate(doc.upload_date);
    const fileSize = typeof doc.size_mb === 'number' ? doc.size_mb.toFixed(2) : doc.size_mb;
    
    return `
        <div class="doc-card" data-filename="${doc.filename}">
            <div class="doc-icon">
                <i class="fas fa-file-pdf"></i>
            </div>
            <div class="doc-info">
                <h4 class="doc-title" title="${doc.filename}">${doc.filename}</h4>
                <p class="doc-details">
                    <span class="doc-size">${fileSize} MB</span>
                    <span class="doc-date">${uploadDate}</span>
                </p>
            </div>
            <div class="doc-actions">
                <button class="btn-small btn-primary" onclick="startLearning('${doc.filename}')" title="학습 시작">
                    <i class="fas fa-graduation-cap"></i>
                    학습하기
                </button>
                <button class="btn-small btn-secondary" onclick="downloadDocument('${doc.filename}')" title="다운로드">
                    <i class="fas fa-download"></i>
                </button>
                <button class="btn-small btn-danger" onclick="deleteDocument('${doc.filename}')" title="삭제">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
}

/**
 * 문서 목록 업데이트
 */
function updateDocumentsList(documents) {
    const container = document.getElementById('recent-docs-container');
    
    if (!container) return;
    
    if (!documents || documents.length === 0) {
        container.innerHTML = `
            <div class="no-docs">
                <i class="fas fa-file-plus"></i>
                <p>아직 업로드된 문서가 없습니다.</p>
                <a href="upload.html" class="btn btn-primary">첫 번째 PDF 업로드하기</a>
            </div>
        `;
        return;
    }
    
    const docsHtml = documents
        .slice(0, 6) // 최대 6개만 표시
        .map(doc => createDocumentCard(doc))
        .join('');
    
    container.innerHTML = docsHtml;
}

// ===== 문서 액션 함수들 =====

/**
 * 학습 시작
 */
function startLearning(filename) {
    const encodedFilename = encodeURIComponent(filename);
    window.location.href = `study.html?file=${encodedFilename}`;
}

/**
 * 문서 다운로드
 */
async function downloadDocument(filename) {
    try {
        const response = await fetch(`${API_BASE_URL}/download/${encodeURIComponent(filename)}`);
        
        if (!response.ok) {
            throw new Error('다운로드에 실패했습니다.');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showMessage('다운로드가 시작되었습니다.', 'success');
    } catch (error) {
        showMessage(`다운로드 실패: ${error.message}`, 'error');
    }
}

/**
 * 문서 삭제
 */
async function deleteDocument(filename) {
    if (!confirm(`'${filename}' 파일을 정말 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        await apiCall(`/delete/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        showMessage('문서가 삭제되었습니다.', 'success');
        
        // 문서 목록 새로고침
        const data = await fetchDocuments();
        updateDocumentsList(data.files);
        updateUploadStatus(data.total_files);
        
    } catch (error) {
        showMessage(`삭제 실패: ${error.message}`, 'error');
    }
}

// ===== 상태 업데이트 함수들 =====

/**
 * 상태 카드 업데이트
 */
function updateStatusCard(cardId, status, text) {
    const card = document.getElementById(cardId);
    if (!card) return;
    
    const statusText = card.querySelector('.status-text');
    const indicator = card.querySelector('.status-indicator');
    
    if (statusText) statusText.textContent = text;
    if (indicator) {
        indicator.className = `status-indicator ${status}`;
    }
}

/**
 * 서버 상태 업데이트
 */
async function updateServerStatus() {
    try {
        const health = await checkServerHealth();
        
        if (health.status === 'healthy') {
            updateStatusCard('server-status', 'online', '서버 정상 작동');
            updateStatusCard('ai-status', 'online', 'AI 서비스 준비됨');
        } else {
            updateStatusCard('server-status', 'warning', '서버 응답 이상');
            updateStatusCard('ai-status', 'warning', 'AI 설정 확인 필요');
        }
    } catch (error) {
        updateStatusCard('server-status', 'offline', '서버 연결 실패');
        updateStatusCard('ai-status', 'offline', 'AI 서비스 중단');
    }
}

/**
 * 업로드 상태 업데이트
 */
function updateUploadStatus(fileCount) {
    if (fileCount > 0) {
        updateStatusCard('upload-status', 'online', `${fileCount}개 파일`);
    } else {
        updateStatusCard('upload-status', 'warning', '업로드된 파일 없음');
    }
}

// ===== 페이지별 초기화 함수들 =====

/**
 * 메인 페이지 초기화
 */
async function initMainPage() {
    try {
        // 서버 상태 확인
        await updateServerStatus();
        
        // 문서 목록 로드
        const data = await fetchDocuments();
        updateDocumentsList(data.files);
        updateUploadStatus(data.total_files);
        
    } catch (error) {
        console.error('Main page initialization failed:', error);
        showMessage('페이지 로드 중 일부 기능에 문제가 발생했습니다.', 'warning');
    }
}

/**
 * 업로드 페이지 초기화
 */
function initUploadPage() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    
    if (!dropZone || !fileInput) return;
    
    // 드래그 앤 드롭 이벤트
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        handleFileSelection(files);
    });
    
    // 파일 선택 이벤트
    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        handleFileSelection(files);
    });
    
    // 업로드 버튼 클릭
    if (uploadBtn) {
        uploadBtn.addEventListener('click', () => fileInput.click());
    }
}

/**
 * 파일 선택 처리
 */
async function handleFileSelection(files) {
    if (files.length === 0) return;
    
    if (isUploading) {
        showMessage('이미 업로드가 진행 중입니다.', 'warning');
        return;
    }
    
    // PDF 파일만 필터링
    const pdfFiles = files.filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length === 0) {
        showMessage('PDF 파일만 업로드할 수 있습니다.', 'error');
        return;
    }
    
    if (pdfFiles.length !== files.length) {
        showMessage(`${files.length - pdfFiles.length}개의 파일이 PDF가 아니어서 제외되었습니다.`, 'warning');
    }
    
    try {
        isUploading = true;
        showMessage(`${pdfFiles.length}개 파일 업로드를 시작합니다.`, 'info');
        
        const { results, errors } = await uploadMultipleFiles(pdfFiles);
        
        if (results.length > 0) {
            showMessage(`${results.length}개 파일이 성공적으로 업로드되었습니다.`, 'success');
        }
        
        if (errors.length > 0) {
            console.error('Upload errors:', errors);
        }
        
        // 파일 입력 초기화
        const fileInput = document.getElementById('file-input');
        if (fileInput) fileInput.value = '';
        
    } catch (error) {
        showMessage(`업로드 실패: ${error.message}`, 'error');
    } finally {
        isUploading = false;
    }
}

// ===== 모달 관련 함수들 =====

/**
 * 모달 표시
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // 백그라운드 스크롤 방지
    }
}

/**
 * 모달 숨김
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// ===== 전역 이벤트 리스너 =====

// 페이지 로드 완료 시
document.addEventListener('DOMContentLoaded', function() {
    // 현재 페이지에 따라 초기화
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    switch (currentPage) {
        case 'index.html':
        case '':
            initMainPage();
            break;
        case 'upload.html':
            initUploadPage();
            break;
        case 'study.html':
            // 학습 페이지 초기화는 별도 파일에서 처리
            break;
    }
    
    // 공통 이벤트 리스너
    setupCommonEventListeners();
});

/**
 * 공통 이벤트 리스너 설정
 */
function setupCommonEventListeners() {
    // 네비게이션 링크 활성화
    const navLinks = document.querySelectorAll('.nav-link');
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage || (currentPage === '' && href === 'index.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    
    // 키보드 이벤트
    document.addEventListener('keydown', (e) => {
        // ESC 키로 모달 닫기
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (modal.style.display === 'block') {
                    modal.style.display = 'none';
                    document.body.style.overflow = 'auto';
                }
            });
        }
    });
}

// ===== CSS 애니메이션 추가 =====
const styles = `
    .loading-spinner {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        color: #7f8c8d;
        font-style: italic;
    }
    
    .drag-over {
        border-color: #3498db !important;
        background-color: rgba(52, 152, 219, 0.1) !important;
    }
    
    .btn-danger {
        background: linear-gradient(45deg, #e74c3c, #c0392b);
        color: white;
    }
    
    .btn-danger:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(231, 76, 60, 0.3);
    }
    
    .doc-actions {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }
    
    .doc-details {
        display: flex;
        gap: 1rem;
        font-size: 0.9rem;
        color: #7f8c8d;
    }
    
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .message-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .message-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 1.2rem;
        opacity: 0.8;
        margin-left: auto;
    }
    
    .message-close:hover {
        opacity: 1;
    }
`;

// 스타일 추가
const styleSheet = document.createElement('style');
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);