import axios from "axios";

// API base configuration
const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL ||
  (import.meta as any).env?.VITE_API_URL ||
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "";

const authClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Types
export interface AuthResponse {
  success: boolean;
  access_token?: string;
  refresh_token?: string;
  user_id?: number;
  organization_id?: number;
  email?: string;
  error?: string;
  errors?: string[];
}

export interface User {
  id: number;
  email: string;
  organization_id: number;
  is_active: boolean;
}

export interface UserResponse {
  id: number;
  email: string;
  organization_id: number;
  is_active: boolean;
}

// Request interceptor for adding auth headers
authClient.interceptors.request.use(
  (config) => {
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

// Response interceptor for token refresh
authClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          const response = await authClient.post("/api/auth/refresh", {
            refresh_token: refreshToken,
          });

          if (response.data.success) {
            localStorage.setItem("auth_token", response.data.access_token);
            originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
            return authClient(originalRequest);
          }
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem("auth_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

// Auth service functions
export const authService = {
  // Register a new user
  async register(
    email: string,
    password: string,
    confirmPassword: string
  ): Promise<AuthResponse> {
    try {
      console.log("Attempting registration with API_BASE_URL:", API_BASE_URL);
      console.log("Registration data:", {
        email,
        password: "***",
        confirm_password: "***",
      });

      const response = await authClient.post("/api/auth/register", {
        email,
        password,
        confirm_password: confirmPassword,
      });

      console.log("Registration response:", response.data);
      return response.data;
    } catch (error: any) {
      console.error("Registration error:", error);
      console.error("Error response:", error.response?.data);
      return {
        success: false,
        error: error.response?.data?.detail || "Registration failed",
      };
    }
  },

  // Login user
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await authClient.post("/api/auth/login", {
        email,
        password,
      });

      if (response.data.success && response.data.access_token) {
        localStorage.setItem("auth_token", response.data.access_token);
        if (response.data.refresh_token) {
          localStorage.setItem("refresh_token", response.data.refresh_token);
        }
      }

      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || "Login failed",
      };
    }
  },

  // Logout user
  async logout(): Promise<void> {
    try {
      await authClient.post("/api/auth/logout");
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("refresh_token");
    }
  },

  // Get current user
  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await authClient.get("/api/auth/me");
      return response.data;
    } catch (error) {
      return null;
    }
  },

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return !!localStorage.getItem("auth_token");
  },

  // Get stored token
  getToken(): string | null {
    return localStorage.getItem("auth_token");
  },
};
