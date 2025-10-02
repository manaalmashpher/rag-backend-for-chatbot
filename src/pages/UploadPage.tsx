import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadForm from "../components/UploadForm";
import { UploadResponse } from "../services/api";

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [recentUpload, setRecentUpload] = useState<UploadResponse | null>(null);

  const handleUploadSuccess = (response: UploadResponse) => {
    setRecentUpload(response);
    // Optionally navigate to status page to monitor the upload
    // navigate(`/status?ingestion_id=${response.ingestion_id}`);
  };

  const handleUploadError = (error: string) => {
    console.error("Upload failed:", error);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Upload Documents
        </h1>
        <p className="text-gray-600">
          Upload your documents for processing and indexing. Choose a chunking
          method to optimize how your content is analyzed.
        </p>
      </div>

      <div className="card">
        <UploadForm
          onUploadSuccess={handleUploadSuccess}
          onUploadError={handleUploadError}
        />
      </div>

      {recentUpload && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="text-sm font-medium text-blue-900 mb-2">
            Upload Successful
          </h3>
          <p className="text-sm text-blue-700 mb-3">
            Your document is being processed. You can monitor its status on the
            Status page.
          </p>
          <button
            onClick={() =>
              navigate(`/status?ingestion_id=${recentUpload.ingestion_id}`)
            }
            className="btn btn-primary text-sm"
          >
            View Status
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadPage;
