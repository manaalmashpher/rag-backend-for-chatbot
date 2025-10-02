"""
Scanned PDF detection service
"""

import io
from PyPDF2 import PdfReader

class ScannedPDFDetector:
    """
    Detects if a PDF is scanned (image-based) rather than text-based
    """
    
    def is_scanned_pdf(self, pdf_content: bytes) -> bool:
        """
        Check if PDF is scanned based on character count per page
        
        Returns True if ≥80% of pages have <20 characters
        """
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            total_pages = len(pdf_reader.pages)
            
            if total_pages == 0:
                return True  # Empty PDF considered scanned
            
            low_text_pages = 0
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                char_count = len(text.strip())
                
                if char_count < 20:
                    low_text_pages += 1
            
            # If 80% or more pages have <20 characters, consider it scanned
            scanned_ratio = low_text_pages / total_pages
            return scanned_ratio >= 0.8
            
        except Exception:
            # If we can't read the PDF, assume it's scanned
            return True
