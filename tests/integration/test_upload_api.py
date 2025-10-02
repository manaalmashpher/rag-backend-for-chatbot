"""
Integration tests for upload API endpoints
"""

import pytest
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.mark.integration
@pytest.mark.api
class TestUploadAPI:
    """Test cases for upload API endpoints"""
    
    def test_upload_file_success(self, client: TestClient, sample_text_content, temp_storage):
        """Test successful file upload."""
        with patch('app.services.scanned_pdf_detector.ScannedPDFDetector.is_scanned_pdf', return_value=False):
            files = {"file": ("test.txt", io.BytesIO(sample_text_content.encode()), "text/plain")}
            data = {"chunk_method": 1, "doc_title": "Test Document"}
            
            response = client.post("/api/upload", files=files, data=data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert "ingestion_id" in response_data
            assert response_data["status"] == "done"  # Upload processes synchronously
            assert "message" in response_data
    
    def test_upload_file_invalid_chunk_method(self, client: TestClient, sample_text_content):
        """Test upload with invalid chunking method."""
        files = {"file": ("test.txt", io.BytesIO(sample_text_content.encode()), "text/plain")}
        data = {"chunk_method": 99, "doc_title": "Test Document"}
        
        response = client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 400
        assert "Invalid chunking method" in response.json()["detail"]
    
    def test_upload_file_too_large(self, client: TestClient, temp_storage):
        """Test upload with file too large."""
        # Create a large file content (simulate > 20MB)
        large_content = b"x" * (21 * 1024 * 1024)  # 21MB
        
        files = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
        data = {"chunk_method": 1, "doc_title": "Large Document"}
        
        response = client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]
    
    def test_upload_file_unsupported_type(self, client: TestClient):
        """Test upload with unsupported file type."""
        files = {"file": ("test.exe", io.BytesIO(b"binary content"), "application/octet-stream")}
        data = {"chunk_method": 1, "doc_title": "Test Document"}
        
        response = client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_upload_file_scanned_pdf(self, client: TestClient, sample_pdf_content, temp_storage):
        """Test upload with scanned PDF."""
        with patch('app.services.scanned_pdf_detector.ScannedPDFDetector.is_scanned_pdf', return_value=True):
            files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
            data = {"chunk_method": 1, "doc_title": "Scanned PDF"}
            
            response = client.post("/api/upload", files=files, data=data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "blocked_scanned_pdf"
            assert "scanned PDF detected" in response_data["message"]
    
    def test_upload_file_duplicate_content(self, client: TestClient, sample_text_content, temp_storage):
        """Test upload with duplicate content (same SHA256)."""
        with patch('app.services.scanned_pdf_detector.ScannedPDFDetector.is_scanned_pdf', return_value=False):
            files = {"file": ("test1.txt", io.BytesIO(sample_text_content.encode()), "text/plain")}
            data = {"chunk_method": 1, "doc_title": "Test Document 1"}
            
            # First upload
            response1 = client.post("/api/upload", files=files, data=data)
            assert response1.status_code == 200
            
            # Second upload with same content
            files2 = {"file": ("test2.txt", io.BytesIO(sample_text_content.encode()), "text/plain")}
            data2 = {"chunk_method": 2, "doc_title": "Test Document 2"}
            
            response2 = client.post("/api/upload", files=files2, data=data2)
            assert response2.status_code == 409
            assert "already exists" in response2.json()["detail"]
    
    def test_upload_file_missing_parameters(self, client: TestClient, sample_text_content):
        """Test upload with missing required parameters."""
        files = {"file": ("test.txt", io.BytesIO(sample_text_content.encode()), "text/plain")}
        data = {"chunk_method": 1}  # Missing doc_title
        
        response = client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_file_sanitized_title(self, client: TestClient, sample_text_content, temp_storage):
        """Test that file titles are properly sanitized."""
        with patch('app.services.scanned_pdf_detector.ScannedPDFDetector.is_scanned_pdf', return_value=False):
            files = {"file": ("test.txt", io.BytesIO(sample_text_content.encode()), "text/plain")}
            data = {"chunk_method": 1, "doc_title": "Test<>Document|With*Invalid?Chars"}
            
            response = client.post("/api/upload", files=files, data=data)
            
            assert response.status_code == 200
            # The title should be sanitized in the database
            # This would require checking the database record in a real test
    
    def test_get_chunking_methods(self, client: TestClient):
        """Test getting available chunking methods."""
        response = client.get("/api/chunking-methods")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "chunking_methods" in response_data
        assert "total" in response_data
        assert response_data["total"] == 8
        
        methods = response_data["chunking_methods"]
        assert len(methods) == 8
        
        # Check that all methods have required fields
        for method in methods:
            assert "id" in method
            assert "name" in method
            assert "description" in method
            assert isinstance(method["id"], int)
            assert isinstance(method["name"], str)
            assert isinstance(method["description"], str)
    
    def test_upload_file_different_formats(self, client: TestClient, temp_storage):
        """Test upload with different supported formats."""
        with patch('app.services.scanned_pdf_detector.ScannedPDFDetector.is_scanned_pdf', return_value=False):
            # Test PDF
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n"
            files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
            data = {"chunk_method": 1, "doc_title": "PDF Document"}
            
            response = client.post("/api/upload", files=files, data=data)
            assert response.status_code == 200
            
            # Test DOCX (mock)
            with patch('app.services.file_processor.DocxDocument') as mock_docx:
                mock_doc = MagicMock()
                mock_paragraph = MagicMock()
                mock_paragraph.text = "DOCX content"
                mock_doc.paragraphs = [mock_paragraph]
                mock_docx.return_value = mock_doc
                
                docx_content = b"mock_docx_content"
                files = {"file": ("test.docx", io.BytesIO(docx_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                data = {"chunk_method": 2, "doc_title": "DOCX Document"}
                
                response = client.post("/api/upload", files=files, data=data)
                assert response.status_code == 200
            
            # Test Markdown
            md_content = b"# Markdown Document\n\nThis is markdown content."
            files = {"file": ("test.md", io.BytesIO(md_content), "text/markdown")}
            data = {"chunk_method": 3, "doc_title": "Markdown Document"}
            
            response = client.post("/api/upload", files=files, data=data)
            assert response.status_code == 200
