import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, AlertCircle, CheckCircle } from "lucide-react";
import { apiService, UploadResponse } from "../services/api";

interface UploadFormProps {
  onUploadSuccess?: (response: UploadResponse) => void;
  onUploadError?: (error: string) => void;
}

const CHUNKING_METHODS = [
  { value: 1, label: "Method 1: Fixed-size chunks (1000 chars)" },
  { value: 2, label: "Method 2: Sentence-based chunks (1000 chars)" },
  { value: 3, label: "Method 3: Paragraph-based chunks (1500 chars)" },
  { value: 4, label: "Method 4: Semantic similarity chunks" },
  { value: 5, label: "Method 5: Hierarchical chunks" },
  { value: 6, label: "Method 6: Overlapping chunks" },
  { value: 7, label: "Method 7: Context-aware chunks" },
  { value: 8, label: "Method 8: Adaptive chunks" },
];

const ALLOWED_FILE_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
    ".docx",
  ],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB

const UploadForm: React.FC<UploadFormProps> = ({
  onUploadSuccess,
  onUploadError,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [chunkMethod, setChunkMethod] = useState<number>(1);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === "file-too-large") {
          setUploadError("File size must be less than 20MB");
        } else if (rejection.errors[0]?.code === "file-invalid-type") {
          setUploadError("Only PDF, DOCX, TXT, and MD files are allowed");
        } else {
          setUploadError("Invalid file type or size");
        }
        return;
      }

      const file = acceptedFiles[0];
      setSelectedFile(file);
      setUploadError(null);
      setUploadSuccess(false);

      // Auto-generate document title from filename if not set
      if (!docTitle) {
        const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
        setDocTitle(nameWithoutExt);
      }
    },
    [docTitle]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ALLOWED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile || !docTitle.trim()) {
      setUploadError("Please select a file and enter a document title");
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const response = await apiService.uploadDocument(
        selectedFile,
        docTitle.trim(),
        chunkMethod
      );

      setUploadSuccess(true);
      onUploadSuccess?.(response);

      // Reset form after successful upload
      setTimeout(() => {
        setSelectedFile(null);
        setDocTitle("");
        setChunkMethod(1);
        setUploadSuccess(false);
      }, 5000); // Increased to 5 seconds to show the message longer
    } catch (error: any) {
      console.error("Upload error:", error);
      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        "Upload failed. Please try again.";
      setUploadError(errorMessage);
      onUploadError?.(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setDocTitle("");
    setChunkMethod(1);
    setUploadError(null);
    setUploadSuccess(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* File Upload Area */}
      <div>
        <label htmlFor="file-upload" className="form-label">
          Select Document
        </label>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-blue-400 bg-blue-50"
              : selectedFile
              ? "border-green-400 bg-green-50"
              : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <input {...getInputProps()} id="file-upload" type="file" />
          <div className="flex flex-col items-center space-y-4">
            {selectedFile ? (
              <>
                <CheckCircle className="h-12 w-12 text-green-600" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </>
            ) : (
              <>
                <Upload className="h-12 w-12 text-gray-400" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    {isDragActive
                      ? "Drop the file here"
                      : "Drag & drop a file here, or click to select"}
                  </p>
                  <p className="text-sm text-gray-500">
                    PDF, DOCX, TXT, or MD files up to 20MB
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Document Title */}
      <div>
        <label htmlFor="docTitle" className="form-label">
          Document Title
        </label>
        <input
          type="text"
          id="docTitle"
          value={docTitle}
          onChange={(e) => setDocTitle(e.target.value)}
          className="form-input"
          placeholder="Enter a title for this document"
          required
          disabled={isUploading}
        />
      </div>

      {/* Chunking Method */}
      <div>
        <label htmlFor="chunkMethod" className="form-label">
          Chunking Method
        </label>
        <select
          id="chunkMethod"
          value={chunkMethod}
          onChange={(e) => setChunkMethod(Number(e.target.value))}
          className="form-input"
          disabled={isUploading}
        >
          {CHUNKING_METHODS.map((method) => (
            <option key={method.value} value={method.value}>
              {method.label}
            </option>
          ))}
        </select>
        <p className="text-sm text-gray-500 mt-1">
          Choose how the document should be split into chunks for processing
        </p>
      </div>

      {/* Error Message */}
      {uploadError && (
        <div className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-700">{uploadError}</p>
        </div>
      )}

      {/* Success Message */}
      {uploadSuccess && (
        <div className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
          <p className="text-sm text-green-700">
            Document uploaded successfully! Processing has started.
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex space-x-4">
        <button
          type="submit"
          disabled={!selectedFile || !docTitle.trim() || isUploading}
          className="btn btn-primary flex-1"
        >
          {isUploading ? (
            <>
              <div className="spinner mr-2" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Upload Document
            </>
          )}
        </button>

        <button
          type="button"
          onClick={handleReset}
          disabled={isUploading}
          className="btn btn-outline"
        >
          Reset
        </button>
      </div>
    </form>
  );
};

export default UploadForm;
