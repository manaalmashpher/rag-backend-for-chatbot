import axios, { AxiosResponse } from "axios";

// API base configuration
const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL ||
  (import.meta as any).env?.VITE_API_URL ||
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for file uploads
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for adding auth headers if needed
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  }
);

// Types for API responses
export interface UploadResponse {
  doc_id: string;
  ingestion_id: string;
}

export interface IngestionStatus {
  id: string;
  status: string;
  progress?: any;
  error?: string;
  blocked_reason?: string;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

export interface SearchResult {
  chunk_id: string;
  doc_id: string;
  method: number;
  page_from?: number;
  page_to?: number;
  hash: string;
  source: string;
  snippet?: string;
  score: number;
  search_type: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total_results: number;
  query: string;
  limit: number;
  search_type: string;
  metadata?: {
    semantic_weight: number;
    lexical_weight: number;
    individual_results: any;
    latency_ms: number;
  };
  latency_ms: number;
}

// API service functions
export const apiService = {
  // Upload a document
  async uploadDocument(
    file: File,
    docTitle: string,
    chunkMethod: number
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_title", docTitle);
    formData.append("chunk_method", chunkMethod.toString());

    const response: AxiosResponse<UploadResponse> = await apiClient.post(
      "/api/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    return response.data;
  },

  // Get ingestion status
  async getIngestionStatus(ingestionId: string): Promise<IngestionStatus> {
    const response: AxiosResponse<IngestionStatus> = await apiClient.get(
      `/api/ingestions/${ingestionId}`
    );
    return response.data;
  },

  // Search documents
  async searchDocuments(query: string): Promise<SearchResponse> {
    const response: AxiosResponse<SearchResponse> = await apiClient.get(
      "/api/search",
      {
        params: { q: query },
      }
    );
    return response.data;
  },
};

export default apiService;
