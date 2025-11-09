import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { authService } from "../services/auth";

// Types
export interface User {
  id: number;
  email: string;
  organization_id: number;
  is_active: boolean;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<boolean>;
  register: (
    email: string,
    password: string,
    confirmPassword: string
  ) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider component
export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = !!user;

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        if (token) {
          const userData = await authService.getCurrentUser();
          if (userData) {
            setUser(userData);
          } else {
            // Token is invalid, clear it
            localStorage.removeItem("auth_token");
            localStorage.removeItem("refresh_token");
          }
        }
      } catch (error) {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("refresh_token");
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await authService.login(email, password);
      if (result.success) {
        setUser({
          id: result.user_id!,
          email: result.email!,
          organization_id: result.organization_id!,
          is_active: true,
        });
        return true;
      } else {
        setError(result.error || "Login failed");
        return false;
      }
    } catch (error) {
      setError("Login failed. Please try again.");
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    email: string,
    password: string,
    confirmPassword: string
  ): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await authService.register(
        email,
        password,
        confirmPassword
      );
      if (result.success) {
        // After successful registration, automatically log in
        return await login(email, password);
      } else {
        setError(result.error || "Registration failed");
        return false;
      }
    } catch (error) {
      setError("Registration failed. Please try again.");
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
  };

  const clearError = () => {
    setError(null);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
