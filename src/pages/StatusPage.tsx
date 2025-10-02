import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import StatusDashboard from "../components/StatusDashboard";

const StatusPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [ingestionId, setIngestionId] = useState<string>(
    searchParams.get("ingestion_id") || ""
  );
  const [submittedIngestionId, setSubmittedIngestionId] = useState<string>(
    searchParams.get("ingestion_id") || ""
  );

  const handleIngestionIdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (ingestionId.trim()) {
      // Update URL with the ingestion ID
      const newSearchParams = new URLSearchParams();
      newSearchParams.set("ingestion_id", ingestionId.trim());
      window.history.replaceState(null, "", `?${newSearchParams.toString()}`);
      // Update the submitted ID to trigger the dashboard update
      setSubmittedIngestionId(ingestionId.trim());
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Ingestion Status
        </h1>
        <p className="text-gray-600">
          Monitor the processing status of your uploaded documents
        </p>
      </div>

      {/* Ingestion ID Input */}
      <div className="card mb-6">
        <form onSubmit={handleIngestionIdSubmit} className="flex space-x-4">
          <div className="flex-1">
            <label htmlFor="ingestionId" className="form-label">
              Ingestion ID
            </label>
            <input
              type="text"
              id="ingestionId"
              value={ingestionId}
              onChange={(e) => setIngestionId(e.target.value)}
              className="form-input"
              placeholder="Enter ingestion ID to view status"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={!ingestionId.trim()}
              className="btn btn-primary"
            >
              View Status
            </button>
          </div>
        </form>
      </div>

      {/* Status Dashboard */}
      <div className="card">
        <StatusDashboard
          key={submittedIngestionId}
          ingestionId={submittedIngestionId || undefined}
        />
      </div>
    </div>
  );
};

export default StatusPage;
