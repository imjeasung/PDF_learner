# PDF 내용 추출 모듈
# PyMuPDF를 사용하여 PDF에서 텍스트, 이미지, 표를 추출합니다.

import fitz  # PyMuPDF
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

class PDFProcessor:
    """PDF 파일을 처리하여 텍스트, 이미지, 표를 추출하는 클래스입니다."""
    
    def __init__(self, data_folder: str = "data"):
        """
        PDF 처리기를 초기화합니다.
        
        Args:
            data_folder: 추출된 데이터를 저장할 폴더
        """
        self.data_folder = data_folder
        self.extracted_folder = f"{data_folder}/extracted"
        
        # 필요한 폴더 생성
        Path(self.extracted_folder).mkdir(parents=True, exist_ok=True)
    
    def extract_pdf_content(self, pdf_path: str) -> Dict:
        """
        PDF 파일에서 모든 내용을 추출합니다.
        
        Args:
            pdf_path: 처리할 PDF 파일 경로
            
        Returns:
            추출된 모든 정보가 담긴 딕셔너리
        """
        try:
            # PDF 파일 열s기
            pdf_document = fitz.open(pdf_path)
            
            # 파일명 추출 (확장자 제거)
            file_name = Path(pdf_path).stem
            
            # 결과 저장용 딕셔너리
            result = {
                "file_name": file_name,
                "file_path": pdf_path,
                "total_pages": len(pdf_document),
                "metadata": self._extract_metadata(pdf_document),
                "toc": self._extract_toc(pdf_document),
                "pages": []
            }
            
            print(f"📄 PDF 처리 시작: {file_name} ({result['total_pages']}페이지)")
            
            # 페이지별 내용 추출
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                page_content = self._extract_page_content(page, page_num + 1, file_name)
                result["pages"].append(page_content)
                
                print(f"  ✅ 페이지 {page_num + 1}/{result['total_pages']} 처리 완료")
            
            # 전체 텍스트 합치기
            result["full_text"] = self._combine_all_text(result["pages"])
            
            # JSON으로 저장
            self._save_extracted_data(result, file_name)
            
            pdf_document.close()
            print(f"🎉 PDF 처리 완료: {file_name}")
            
            return result
            
        except Exception as e:
            print(f"❌ PDF 처리 중 오류 발생: {str(e)}")
            raise Exception(f"PDF 처리 실패: {str(e)}")
    
    def _extract_metadata(self, pdf_document) -> Dict:
        """PDF 메타데이터를 추출합니다."""
        try:
            metadata = pdf_document.metadata
            return {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", "")
            }
        except:
            return {}
    
    def _extract_toc(self, pdf_document) -> List[Dict]:
        """목차(Table of Contents)를 추출합니다."""
        try:
            toc = pdf_document.get_toc()
            formatted_toc = []
            
            for item in toc:
                if len(item) >= 3:
                    formatted_toc.append({
                        "level": item[0],  # 목차 레벨 (1, 2, 3...)
                        "title": item[1],  # 제목
                        "page": item[2]    # 페이지 번호
                    })
            
            return formatted_toc
        except:
            return []
    
    def _extract_page_content(self, page, page_num: int, file_name: str) -> Dict:
        """단일 페이지에서 텍스트와 이미지를 추출합니다."""
        page_content = {
            "page_number": page_num,
            "text": "",
            "images": [],
            "tables": [],  # 표는 향후 확장 가능
            "text_blocks": []
        }
        
        try:
            # 텍스트 추출
            page_content["text"] = page.get_text()
            
            # 텍스트 블록 추출 (위치 정보 포함)
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:  # 텍스트 블록인 경우
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"]
                        block_text += "\n"
                    
                    if block_text.strip():
                        page_content["text_blocks"].append({
                            "text": block_text.strip(),
                            "bbox": block["bbox"],  # 위치 정보
                            "font_info": self._get_font_info(block)
                        })
            
            # 이미지 추출
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                image_info = self._extract_image(page, img, img_index, page_num, file_name)
                if image_info:
                    page_content["images"].append(image_info)
            
        except Exception as e:
            print(f"  ⚠️ 페이지 {page_num} 처리 중 오류: {str(e)}")
        
        return page_content
    
    def _get_font_info(self, block) -> Dict:
        """텍스트 블록의 폰트 정보를 추출합니다."""
        try:
            if "lines" in block and len(block["lines"]) > 0:
                first_line = block["lines"][0]
                if "spans" in first_line and len(first_line["spans"]) > 0:
                    span = first_line["spans"][0]
                    return {
                        "font": span.get("font", ""),
                        "size": span.get("size", 0),
                        "color": span.get("color", 0),
                        "flags": span.get("flags", 0)  # 볼드, 이탤릭 등
                    }
        except:
            pass
        return {}
    
    def _extract_image(self, page, img, img_index: int, page_num: int, file_name: str) -> Optional[Dict]:
        """페이지에서 이미지를 추출하고 저장합니다."""
        try:
            # 이미지 정보 가져오기
            xref = img[0]
            pix = fitz.Pixmap(page.parent, xref)
            
            # RGB로 변환 (CMYK인 경우)
            if pix.n - pix.alpha < 4:
                # 이미지 저장 경로
                image_filename = f"{file_name}_page{page_num}_img{img_index + 1}.png"
                image_path = f"{self.extracted_folder}/{image_filename}"
                
                pix.save(image_path)
                pix = None  # 메모리 해제
                
                return {
                    "filename": image_filename,
                    "path": image_path,
                    "page": page_num,
                    "index": img_index + 1
                }
            else:
                # CMYK 이미지는 RGB로 변환
                pix_rgb = fitz.Pixmap(fitz.csRGB, pix)
                image_filename = f"{file_name}_page{page_num}_img{img_index + 1}.png"
                image_path = f"{self.extracted_folder}/{image_filename}"
                
                pix_rgb.save(image_path)
                pix_rgb = None
                pix = None
                
                return {
                    "filename": image_filename,
                    "path": image_path,
                    "page": page_num,
                    "index": img_index + 1
                }
                
        except Exception as e:
            print(f"    ⚠️ 이미지 추출 실패 (페이지 {page_num}, 이미지 {img_index + 1}): {str(e)}")
            return None
    
    def _combine_all_text(self, pages: List[Dict]) -> str:
        """모든 페이지의 텍스트를 하나로 합칩니다."""
        full_text = ""
        for page in pages:
            if page["text"].strip():
                full_text += f"\n=== 페이지 {page['page_number']} ===\n"
                full_text += page["text"]
                full_text += "\n"
        return full_text.strip()
    
    def _save_extracted_data(self, data: Dict, file_name: str) -> str:
        """추출된 데이터를 JSON 파일로 저장합니다."""
        try:
            json_path = f"{self.extracted_folder}/{file_name}_extracted.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"  💾 추출 데이터 저장: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"  ⚠️ 데이터 저장 실패: {str(e)}")
            return ""
    
    def get_text_summary(self, pdf_path: str) -> Dict:
        """PDF의 간단한 텍스트 요약 정보를 반환합니다."""
        try:
            result = self.extract_pdf_content(pdf_path)
            
            # 간단한 통계 계산
            total_chars = len(result["full_text"])
            total_words = len(result["full_text"].split())
            total_images = sum(len(page["images"]) for page in result["pages"])
            
            return {
                "file_name": result["file_name"],
                "total_pages": result["total_pages"],
                "total_characters": total_chars,
                "total_words": total_words,
                "total_images": total_images,
                "has_toc": len(result["toc"]) > 0,
                "toc_items": len(result["toc"])
            }
            
        except Exception as e:
            return {"error": str(e)}

# 사용 예시 함수
def process_single_pdf(pdf_path: str) -> Dict:
    """
    단일 PDF 파일을 처리하는 간단한 함수입니다.
    
    Args:
        pdf_path: 처리할 PDF 파일 경로
        
    Returns:
        처리 결과
    """
    processor = PDFProcessor()
    return processor.extract_pdf_content(pdf_path)

# 테스트용 메인 함수
if __name__ == "__main__":
    # 테스트 코드
    test_pdf = r"C:\Users\limjeasung\Desktop\클로드코드\pdflearner\uploads\test.pdf"  # 테스트할 PDF 파일 경로
    
    if os.path.exists(test_pdf):
        print("🧪 PDF 처리 테스트 시작...")
        result = process_single_pdf(test_pdf)
        print(f"📊 처리 결과: {result['total_pages']}페이지, 텍스트 {len(result['full_text'])}자")
    else:
        print(f"❌ 테스트 파일이 없습니다: {test_pdf}")
        print("💡 uploads/ 폴더에 test.pdf 파일을 넣고 다시 실행해보세요.")