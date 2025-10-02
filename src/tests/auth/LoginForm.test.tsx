import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, beforeEach, expect } from "vitest";
import { LoginForm } from "../../components/auth/LoginForm";

// Mock the auth context
const mockLogin = vi.fn();
const mockClearError = vi.fn();

const mockAuthContext = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null as string | null,
  login: mockLogin,
  register: vi.fn(),
  logout: vi.fn(),
  clearError: mockClearError,
};

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => mockAuthContext,
}));

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form correctly", () => {
    render(<LoginForm />);

    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  it("shows error message when error exists", () => {
    // Temporarily modify the mock context
    const originalError = mockAuthContext.error;
    mockAuthContext.error = "Invalid credentials";

    render(<LoginForm />);

    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();

    // Restore original error
    mockAuthContext.error = originalError;
  });

  it("calls login with form data on submit", async () => {
    mockLogin.mockResolvedValue(true);

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("shows loading state during login", async () => {
    mockLogin.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    expect(screen.getByText("Logging in...")).toBeInTheDocument();
  });

  it("calls onSuccess when login succeeds", async () => {
    const mockOnSuccess = vi.fn();
    mockLogin.mockResolvedValue(true);

    render(<LoginForm onSuccess={mockOnSuccess} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it("shows register link when onSwitchToRegister is provided", () => {
    const mockOnSwitchToRegister = vi.fn();

    render(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />);

    expect(screen.getByText("Don't have an account?")).toBeInTheDocument();
    expect(screen.getByText("Register here")).toBeInTheDocument();
  });

  it("calls onSwitchToRegister when register link is clicked", () => {
    const mockOnSwitchToRegister = vi.fn();

    render(<LoginForm onSwitchToRegister={mockOnSwitchToRegister} />);

    fireEvent.click(screen.getByText("Register here"));

    expect(mockOnSwitchToRegister).toHaveBeenCalled();
  });
});
