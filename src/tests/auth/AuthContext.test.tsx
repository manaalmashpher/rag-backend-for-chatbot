import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, beforeEach, expect } from "vitest";
import { AuthProvider, useAuth } from "../../contexts/AuthContext";
import { authService } from "../../services/auth";

// Mock the auth service
vi.mock("../../services/auth", () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    isAuthenticated: vi.fn(),
  },
}));

// Test component that uses the auth context
const TestComponent = () => {
  const { user, isAuthenticated, login, register, logout, error } = useAuth();

  return (
    <div>
      <div data-testid="user">{user ? user.email : "No user"}</div>
      <div data-testid="isAuthenticated">
        {isAuthenticated ? "true" : "false"}
      </div>
      <div data-testid="error">{error || "No error"}</div>
      <button onClick={() => login("test@example.com", "password")}>
        Login
      </button>
      <button
        onClick={() => register("test@example.com", "password", "password")}
      >
        Register
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  it("provides initial state correctly", () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId("user")).toHaveTextContent("No user");
    expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("error")).toHaveTextContent("No error");
  });

  it("handles successful login", async () => {
    const mockLoginResponse = {
      success: true,
      user_id: 1,
      email: "test@example.com",
      organization_id: 1,
      access_token: "access_token",
      refresh_token: "refresh_token",
    };

    (authService.login as any).mockResolvedValue(mockLoginResponse);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText("Login"));

    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("true");
    });
  });

  it("handles failed login", async () => {
    const mockLoginResponse = {
      success: false,
      error: "Invalid credentials",
    };

    (authService.login as any).mockResolvedValue(mockLoginResponse);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText("Login"));

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent(
        "Invalid credentials"
      );
    });
  });

  it("handles successful registration", async () => {
    const mockRegisterResponse = {
      success: true,
      user_id: 1,
      email: "test@example.com",
      organization_id: 1,
    };

    const mockLoginResponse = {
      success: true,
      user_id: 1,
      email: "test@example.com",
      organization_id: 1,
      access_token: "access_token",
      refresh_token: "refresh_token",
    };

    (authService.register as any).mockResolvedValue(mockRegisterResponse);
    (authService.login as any).mockResolvedValue(mockLoginResponse);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText("Register"));

    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("true");
    });
  });

  it("handles failed registration", async () => {
    const mockRegisterResponse = {
      success: false,
      error: "Email already exists",
    };

    (authService.register as any).mockResolvedValue(mockRegisterResponse);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText("Register"));

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent(
        "Email already exists"
      );
    });
  });

  it("handles logout", async () => {
    // First login
    const mockLoginResponse = {
      success: true,
      user_id: 1,
      email: "test@example.com",
      organization_id: 1,
      access_token: "access_token",
      refresh_token: "refresh_token",
    };

    (authService.login as any).mockResolvedValue(mockLoginResponse);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText("Login"));

    await waitFor(() => {
      expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("true");
    });

    // Then logout
    fireEvent.click(screen.getByText("Logout"));

    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("No user");
      expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("false");
    });
  });

  it("checks for existing token on mount", async () => {
    localStorage.setItem("auth_token", "existing_token");

    const mockUserResponse = {
      id: 1,
      email: "test@example.com",
      organization_id: 1,
      is_active: true,
    };

    (authService.getCurrentUser as any).mockResolvedValue(mockUserResponse);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
      expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("true");
    });
  });

  it("clears invalid token on mount", async () => {
    localStorage.setItem("auth_token", "invalid_token");

    (authService.getCurrentUser as any).mockResolvedValue(null);

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(localStorage.getItem("auth_token")).toBeNull();
      expect(screen.getByTestId("isAuthenticated")).toHaveTextContent("false");
    });
  });
});
