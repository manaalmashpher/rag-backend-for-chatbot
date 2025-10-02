"""
Unit tests for FileProcessor
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.file_processor import FileProcessor

@pytest.mark.unit
class TestFileProcessor:
    """Test cases for FileProcessor"""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FileProcessor()
    
    def test_extract_pdf_text_success(self):
        """Test successful PDF text extraction."""
        # Mock PDF content
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.file_processor.PdfReader') as mock_pdf_reader:
            # Mock PDF reader and pages
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Sample PDF text content"
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.processor._extract_pdf_text(mock_pdf_content)
            
            assert result == "Sample PDF text content"
            mock_pdf_reader.assert_called_once()
    
    def test_extract_pdf_text_empty(self):
        """Test PDF text extraction with empty content."""
        mock_pdf_content = b"mock_pdf_content"
        
        with patch('app.services.file_processor.PdfReader') as mock_pdf_reader:
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""  # Empty text
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance
            
            result = self.processor._extract_pdf_text(mock_pdf_content)
            
            assert result is None
    
    def test_extract_pdf_text_exception(self):
        """Test PDF text extraction with exception."""
        mock_pdf_content = b"invalid_pdf_content"
        
        with patch('app.services.file_processor.PdfReader') as mock_pdf_reader:
            mock_pdf_reader.side_effect = Exception("PDF parsing error")
            
            result = self.processor._extract_pdf_text(mock_pdf_content)
            
            assert result is None
    
    def test_extract_docx_text_success(self):
        """Test successful DOCX text extraction."""
        mock_docx_content = b"mock_docx_content"
        
        with patch('app.services.file_processor.DocxDocument') as mock_docx:
            # Mock DOCX document and paragraphs
            mock_doc_instance = MagicMock()
            mock_paragraph = MagicMock()
            mock_paragraph.text = "Sample DOCX text content"
            mock_doc_instance.paragraphs = [mock_paragraph]
            mock_docx.return_value = mock_doc_instance
            
            result = self.processor._extract_docx_text(mock_docx_content)
            
            assert result == "Sample DOCX text content"
            mock_docx.assert_called_once()
    
    def test_extract_docx_text_empty(self):
        """Test DOCX text extraction with empty content."""
        mock_docx_content = b"mock_docx_content"
        
        with patch('app.services.file_processor.DocxDocument') as mock_docx:
            mock_doc_instance = MagicMock()
            mock_paragraph = MagicMock()
            mock_paragraph.text = ""  # Empty text
            mock_doc_instance.paragraphs = [mock_paragraph]
            mock_docx.return_value = mock_doc_instance
            
            result = self.processor._extract_docx_text(mock_docx_content)
            
            assert result is None
    
    def test_extract_docx_text_exception(self):
        """Test DOCX text extraction with exception."""
        mock_docx_content = b"invalid_docx_content"
        
        with patch('app.services.file_processor.DocxDocument') as mock_docx:
            mock_docx.side_effect = Exception("DOCX parsing error")
            
            result = self.processor._extract_docx_text(mock_docx_content)
            
            assert result is None
    
    def test_extract_text_file_utf8(self):
        """Test text file extraction with UTF-8 encoding."""
        text_content = "Sample text content with UTF-8: émojis 🚀"
        mock_content = text_content.encode('utf-8')
        
        result = self.processor._extract_text_file(mock_content)
        
        assert result == text_content
    
    def test_extract_text_file_latin1_fallback(self):
        """Test text file extraction with Latin-1 fallback."""
        text_content = "Sample text content with Latin-1: café"
        mock_content = text_content.encode('latin-1')
        
        result = self.processor._extract_text_file(mock_content)
        
        assert result == text_content
    
    def test_extract_text_file_exception(self):
        """Test text file extraction with exception."""
        # Create a mock bytes object that will raise an exception when decoded
        class MockBytes:
            def decode(self, encoding):
                raise Exception("Decode error")
        
        mock_content = MockBytes()
        
        result = self.processor._extract_text_file(mock_content)
        
        # The method should return None when it can't decode the content
        assert result is None
    
    def test_extract_text_pdf_mime_type(self):
        """Test extract_text with PDF MIME type."""
        mock_content = b"mock_pdf_content"
        
        with patch.object(self.processor, '_extract_pdf_text') as mock_extract:
            mock_extract.return_value = "PDF text"
            
            result = self.processor.extract_text(mock_content, 'application/pdf')
            
            assert result == "PDF text"
            mock_extract.assert_called_once_with(mock_content)
    
    def test_extract_text_docx_mime_type(self):
        """Test extract_text with DOCX MIME type."""
        mock_content = b"mock_docx_content"
        
        with patch.object(self.processor, '_extract_docx_text') as mock_extract:
            mock_extract.return_value = "DOCX text"
            
            result = self.processor.extract_text(mock_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            
            assert result == "DOCX text"
            mock_extract.assert_called_once_with(mock_content)
    
    def test_extract_text_plain_mime_type(self):
        """Test extract_text with plain text MIME type."""
        mock_content = b"plain text content"
        
        with patch.object(self.processor, '_extract_text_file') as mock_extract:
            mock_extract.return_value = "Plain text"
            
            result = self.processor.extract_text(mock_content, 'text/plain')
            
            assert result == "Plain text"
            mock_extract.assert_called_once_with(mock_content)
    
    def test_extract_text_markdown_mime_type(self):
        """Test extract_text with markdown MIME type."""
        mock_content = b"# Markdown content"
        
        with patch.object(self.processor, '_extract_text_file') as mock_extract:
            mock_extract.return_value = "# Markdown content"
            
            result = self.processor.extract_text(mock_content, 'text/markdown')
            
            assert result == "# Markdown content"
            mock_extract.assert_called_once_with(mock_content)
    
    def test_extract_text_unsupported_mime_type(self):
        """Test extract_text with unsupported MIME type."""
        mock_content = b"unsupported content"
        
        result = self.processor.extract_text(mock_content, 'application/unsupported')
        
        assert result is None
