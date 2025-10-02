import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  FileText,
} from "lucide-react";
import { apiService, IngestionStatus } from "../services/api";

interface StatusDashboardProps {
  ingestionId?: string;
}

const StatusDashboard: React.FC<StatusDashboardProps> = ({ ingestionId }) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Memoize the ingestion ID to prevent unnecessary re-renders
  const selectedIngestionId = useMemo(() => ingestionId || null, [ingestionId]);

  // Query for ingestion status
  const {
    data: status,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["ingestion-status", selectedIngestionId],
    queryFn: () => apiService.getIngestionStatus(selectedIngestionId!),
    enabled: !!selectedIngestionId,
    // Add request deduplication and caching
    staleTime: 2000, // Consider data fresh for 2 seconds
    gcTime: 30000, // Keep in cache for 30 seconds (replaces cacheTime)
    refetchInterval: (query) => {
      // Only poll if the status is actively processing
      if (
        query.state.data &&
        (query.state.data.status === "processing" ||
          query.state.data.status === "indexing")
      ) {
        // Poll every 10 seconds for active processing (less aggressive)
        return 10000;
      }
      // No polling for completed, failed, or pending states
      return false;
    },
    // Add retry configuration
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      case "processing":
      case "indexing":
        return <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800 border-green-200";
      case "failed":
        return "bg-red-100 text-red-800 border-red-200";
      case "processing":
      case "indexing":
        return "bg-blue-100 text-blue-800 border-blue-200";
      default:
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
    }
  };

  const getStatusMessage = (status: string) => {
    switch (status) {
      case "pending":
        return "Document is queued for processing";
      case "processing":
        return "Extracting text and preparing chunks";
      case "indexing":
        return "Creating embeddings and indexing content";
      case "completed":
        return "Document processing completed successfully";
      case "failed":
        return "Document processing failed";
      default:
        return "Unknown status";
    }
  };

  const handleRefresh = () => {
    console.log("Refresh button clicked");
    setIsRefreshing(true);
    refetch()
      .then((result) => {
        console.log("Refetch completed:", result);
        // Show refreshing state for a moment to give visual feedback
        setTimeout(() => setIsRefreshing(false), 500);
      })
      .catch((error) => {
        console.error("Refetch failed:", error);
        setIsRefreshing(false);
      });
  };

  if (!selectedIngestionId) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No Ingestion Selected
        </h3>
        <p className="text-gray-600">
          Enter an ingestion ID to view its status, or upload a document to get
          started.
        </p>
      </div>
    );
  }

  if (isLoading && !status) {
    return (
      <div className="text-center py-12">
        <RefreshCw className="h-8 w-8 text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Loading status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Error Loading Status
        </h3>
        <p className="text-gray-600 mb-4">
          {error instanceof Error
            ? error.message
            : "Failed to load ingestion status"}
        </p>
        <button onClick={handleRefresh} className="btn btn-primary">
          Try Again
        </button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Status Not Found
        </h3>
        <p className="text-gray-600">
          No status found for ingestion ID: {selectedIngestionId}
        </p>
      </div>
    );
  }

  // Type assertion to ensure TypeScript knows the structure
  const statusData = status as IngestionStatus;

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Ingestion Status
          </h2>
          <p className="text-sm text-gray-600">ID: {statusData.id}</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading || isRefreshing}
          className="btn btn-outline flex items-center space-x-2"
        >
          <RefreshCw
            className={`h-4 w-4 ${
              isLoading || isRefreshing ? "animate-spin" : ""
            }`}
          />
          <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
        </button>
      </div>

      {/* Status Card */}
      <div className="card">
        <div className="flex items-center space-x-4 mb-6">
          {getStatusIcon(statusData.status)}
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              {statusData.status.charAt(0).toUpperCase() +
                statusData.status.slice(1)}
            </h3>
            <p className="text-sm text-gray-600">
              {getStatusMessage(statusData.status)}
            </p>
          </div>
          <div
            className={`ml-auto px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(
              statusData.status
            )}`}
          >
            {statusData.status}
          </div>
        </div>

        {/* Document Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Ingestion ID
            </h4>
            <p className="text-sm text-gray-900 font-mono">{statusData.id}</p>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Created At
            </h4>
            <p className="text-sm text-gray-900">
              {new Date(statusData.created_at).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Processing Info */}
        {statusData.started_at && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Started At
              </h4>
              <p className="text-sm text-gray-900">
                {new Date(statusData.started_at).toLocaleString()}
              </p>
            </div>
            {statusData.finished_at && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Finished At
                </h4>
                <p className="text-sm text-gray-900">
                  {new Date(statusData.finished_at).toLocaleString()}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Blocked Reason */}
        {statusData.blocked_reason && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <h4 className="text-sm font-medium text-yellow-800 mb-2">
              Blocked Reason
            </h4>
            <p className="text-sm text-yellow-700">
              {statusData.blocked_reason}
            </p>
          </div>
        )}

        {/* Error */}
        {statusData.error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="text-sm font-medium text-red-800 mb-2">Error</h4>
            <p className="text-sm text-red-700">{statusData.error}</p>
          </div>
        )}

        {/* Progress Indicator */}
        {statusData.status === "processing" ||
        statusData.status === "indexing" ? (
          <div className="mt-6">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Processing Progress</span>
              <span>In progress...</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 animate-pulse"
                style={{
                  width: "100%",
                }}
              />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default StatusDashboard;
