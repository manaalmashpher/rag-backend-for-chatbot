import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, FileText, AlertCircle } from "lucide-react";
import { apiService, SearchResponse } from "../services/api";

interface SearchInterfaceProps {
  initialQuery?: string;
}

const SearchInterface: React.FC<SearchInterfaceProps> = ({
  initialQuery = "",
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [searchQuery, setSearchQuery] = useState(initialQuery);

  const {
    data: searchResults,
    isLoading,
    error,
    refetch,
  } = useQuery<SearchResponse>({
    queryKey: ["search", searchQuery],
    queryFn: () => apiService.searchDocuments(searchQuery),
    enabled: !!searchQuery.trim(),
    staleTime: 0, // Always consider data stale to ensure fresh searches
    gcTime: 0, // Don't cache search results
    retry: 1, // Only retry once on failure
    retryDelay: 1000, // Wait 1 second before retry
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      const trimmedQuery = query.trim();
      setSearchQuery(trimmedQuery);
      // Don't clear the input - keep the query visible
    }
  };

  const handleClear = () => {
    setQuery("");
    setSearchQuery("");
  };

  const handleViewDocument = (docId: string) => {
    // For now, we'll show an alert with the document ID
    // In a real app, this would navigate to a document view page
    alert(
      `Viewing document: ${docId}\n\nNote: Document viewer not yet implemented.`
    );
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1);
  };

  const truncateText = (text: string | null, maxLength: number = 200) => {
    if (!text) return "";
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  const highlightQuery = (text: string | null, query: string) => {
    if (!text) return "";
    if (!query.trim()) return text;

    const regex = new RegExp(
      `(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi"
    );
    const parts = text.split(regex);

    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex space-x-4">
          <div className="flex-1">
            <label htmlFor="searchQuery" className="form-label">
              Search Documents
            </label>
            <div className="relative flex items-center">
              <Search className="absolute left-3 h-4 w-4 text-gray-400 z-10" />
              <input
                type="text"
                id="searchQuery"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="form-input pl-10"
                placeholder="Enter your search query..."
                disabled={isLoading}
              />
            </div>
          </div>
          <div className="flex items-end space-x-2">
            <button
              type="submit"
              disabled={!query.trim() || isLoading}
              className="btn btn-primary"
            >
              {isLoading ? (
                <>
                  <div className="spinner mr-2" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </>
              )}
            </button>
            {searchQuery && (
              <button
                type="button"
                onClick={handleClear}
                className="btn btn-outline"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Search Results */}
      {searchQuery && (
        <div className="space-y-4">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              Search Results
            </h2>
            {searchResults && (
              <div className="text-sm text-gray-600">
                {searchResults.results?.length || 0} results found
                {searchResults.latency_ms && (
                  <span className="ml-2">({searchResults.latency_ms}ms)</span>
                )}
              </div>
            )}
          </div>

          {/* Error State */}
          {error && (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Search Error
              </h3>
              <p className="text-gray-600 mb-4">
                {error instanceof Error
                  ? error.message
                  : "Failed to search documents"}
              </p>
              <button onClick={() => refetch()} className="btn btn-primary">
                Try Again
              </button>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <div className="spinner mx-auto mb-4" />
              <p className="text-gray-600">Searching documents...</p>
            </div>
          )}

          {/* No Results */}
          {searchResults &&
            (!searchResults.results || searchResults.results.length === 0) &&
            !isLoading && (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No Results Found
                </h3>
                <p className="text-gray-600">
                  Try different keywords or check if documents have been
                  processed.
                </p>
              </div>
            )}

          {/* Results List */}
          {searchResults &&
            searchResults.results &&
            searchResults.results.length > 0 && (
              <div className="space-y-4">
                {/* Search Parameters */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">
                    Search Parameters
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Total Results:</span>
                      <span className="ml-1 font-medium">
                        {searchResults.total_results || 0}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Search Type:</span>
                      <span className="ml-1 font-medium">
                        {searchResults.search_type || "N/A"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Semantic Weight:</span>
                      <span className="ml-1 font-medium">
                        {searchResults.metadata?.semantic_weight || "N/A"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Lexical Weight:</span>
                      <span className="ml-1 font-medium">
                        {searchResults.metadata?.lexical_weight || "N/A"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Results */}
                {searchResults.results?.map((result, index) => (
                  <div
                    key={`${result.doc_id}-${result.chunk_id}`}
                    className="card"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium text-gray-500">
                          #{index + 1}
                        </span>
                        <span className="text-sm font-medium text-blue-600">
                          Score: {formatScore(result.score)}%
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 text-sm text-gray-500">
                        <span>Method {result.method}</span>
                        {result.page_from && result.page_to && (
                          <span>
                            • Pages {result.page_from}-{result.page_to}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mb-3">
                      <h4 className="text-sm font-medium text-gray-700 mb-1">
                        {result.source || `Document: ${result.doc_id}`}
                      </h4>
                      <p className="text-sm text-gray-500">
                        Chunk: {result.chunk_id}
                      </p>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-800 leading-relaxed">
                        {result.snippet ? (
                          highlightQuery(
                            truncateText(result.snippet),
                            searchQuery
                          )
                        ) : (
                          <span className="text-gray-500 italic">
                            No snippet available for this result
                          </span>
                        )}
                      </p>
                    </div>

                    <div className="mt-3 flex items-center justify-between">
                      <div className="text-xs text-gray-500">
                        <span>Document ID: {result.doc_id}</span>
                        <span className="mx-2">•</span>
                        <span>Chunk ID: {result.chunk_id}</span>
                      </div>
                      <button
                        onClick={() => handleViewDocument(result.doc_id)}
                        className="px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 hover:border-blue-300 hover:text-blue-700 transition-colors duration-200"
                      >
                        View Full Document
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
        </div>
      )}

      {/* Search Tips */}
      {!searchQuery && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-900 mb-3">
            Search Tips
          </h3>
          <ul className="text-sm text-blue-800 space-y-2 list-disc list-inside">
            <li>Use natural language queries for best results</li>
            <li>
              Try different keywords if you don't find what you're looking for
            </li>
            <li>
              The search combines semantic and lexical matching for
              comprehensive results
            </li>
            <li>Results are ranked by relevance score</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default SearchInterface;
