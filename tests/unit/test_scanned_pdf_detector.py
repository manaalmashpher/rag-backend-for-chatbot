"""
Unit tests for ScannedPDFDetector
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.scanned_pdf_detector import ScannedPDFDetector

@pytest.mark.unit
class TestScannedPDFDetector:
    """Test cases for ScannedPDFDetector"""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ScannedPDFDetector()
    
    def test_is_scanned_pdf_empty_pdf(self):
        """Test detection with empty PDF."""
        empty_pdf = b""
        
        result = self.detector.is_scanned_pdf(empty_pdf)
        
        assert result is True
    
    def test_is_scanned_pdf_single_page_low_text(self):
        """Test detection with single page having low text."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Hi"  # Less than 20 characters
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is True
    
    def test_is_scanned_pdf_single_page_high_text(self):
        """Test detection with single page having high text."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is a long text content that has more than twenty characters and should not be considered scanned"
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is False
    
    def test_is_scanned_pdf_multiple_pages_mixed(self):
        """Test detection with multiple pages, some low text, some high text."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            
            # Create 5 pages: 4 with low text, 1 with high text (80% low text)
            mock_pages = []
            for i in range(4):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Hi"  # Low text
                mock_pages.append(mock_page)
            
            mock_page_high = MagicMock()
            mock_page_high.extract_text.return_value = "This is a long text content that has more than twenty characters and should not be considered scanned"
            mock_pages.append(mock_page_high)
            
            mock_reader_instance.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is True  # 80% of pages have low text
    
    def test_is_scanned_pdf_multiple_pages_mostly_high_text(self):
        """Test detection with multiple pages, mostly high text."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            
            # Create 5 pages: 1 with low text, 4 with high text (20% low text)
            mock_pages = []
            
            mock_page_low = MagicMock()
            mock_page_low.extract_text.return_value = "Hi"  # Low text
            mock_pages.append(mock_page_low)
            
            for i in range(4):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "This is a long text content that has more than twenty characters and should not be considered scanned"
                mock_pages.append(mock_page)
            
            mock_reader_instance.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is False  # Only 20% of pages have low text
    
    def test_is_scanned_pdf_exactly_80_percent_low_text(self):
        """Test detection with exactly 80% of pages having low text."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            
            # Create 5 pages: 4 with low text, 1 with high text (exactly 80% low text)
            mock_pages = []
            for i in range(4):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "Hi"  # Low text
                mock_pages.append(mock_page)
            
            mock_page_high = MagicMock()
            mock_page_high.extract_text.return_value = "This is a long text content that has more than twenty characters and should not be considered scanned"
            mock_pages.append(mock_page_high)
            
            mock_reader_instance.pages = mock_pages
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is True  # Exactly 80% of pages have low text
    
    def test_is_scanned_pdf_exception_handling(self):
        """Test detection with exception during PDF reading."""
        mock_pdf_content = b"invalid_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_pdf_reader.side_effect = Exception("PDF parsing error")
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is True  # Should return True on exception
    
    def test_is_scanned_pdf_whitespace_handling(self):
        """Test detection with whitespace-only text."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "   \n\t   "  # Whitespace only
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is True  # Whitespace-only text should be considered low text
    
    def test_is_scanned_pdf_boundary_conditions(self):
        """Test detection with boundary conditions around 20 characters."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.scanned_pdf_detector.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            
            # Test with exactly 20 characters
            mock_page_20 = MagicMock()
            mock_page_20.extract_text.return_value = "12345678901234567890"  # Exactly 20 chars
            mock_reader_instance.pages = [mock_page_20]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is False  # Exactly 20 characters should not be considered low text
            
            # Test with 19 characters
            mock_page_19 = MagicMock()
            mock_page_19.extract_text.return_value = "1234567890123456789"  # 19 chars
            mock_reader_instance.pages = [mock_page_19]
            
            result = self.detector.is_scanned_pdf(mock_pdf_content)
            
            assert result is True  # 19 characters should be considered low text
