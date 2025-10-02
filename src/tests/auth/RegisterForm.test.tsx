import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, beforeEach, expect } from "vitest";
import { RegisterForm } from "../../components/auth/RegisterForm";

// Mock the auth context
const mockRegister = vi.fn();
const mockClearError = vi.fn();

const mockAuthContext = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null as string | null,
  login: vi.fn(),
  register: mockRegister,
  logout: vi.fn(),
  clearError: mockClearError,
};

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => mockAuthContext,
}));

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders register form correctly", () => {
    render(<RegisterForm />);

    expect(
      screen.getByRole("heading", { name: "Register" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Register" })
    ).toBeInTheDocument();
  });

  it("shows error message when error exists", () => {
    // Temporarily modify the mock context
    const originalError = mockAuthContext.error;
    mockAuthContext.error = "Registration failed";

    render(<RegisterForm />);

    expect(screen.getByText("Registration failed")).toBeInTheDocument();

    // Restore original error
    mockAuthContext.error = originalError;
  });

  it("validates password strength and shows errors", async () => {
    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "weak" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "weak" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(
        screen.getByText("Password must be at least 8 characters long")
      ).toBeInTheDocument();
    });
  });

  it("validates password confirmation match", async () => {
    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "TestPassword123!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "DifferentPassword123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
  });

  it("calls register with form data on submit when validation passes", async () => {
    mockRegister.mockResolvedValue(true);

    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "TestPassword123!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "TestPassword123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        "test@example.com",
        "TestPassword123!",
        "TestPassword123!"
      );
    });
  });

  it("shows loading state during registration", async () => {
    mockRegister.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<RegisterForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "TestPassword123!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "TestPassword123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    expect(screen.getByText("Creating account...")).toBeInTheDocument();
  });

  it("calls onSuccess when registration succeeds", async () => {
    const mockOnSuccess = vi.fn();
    mockRegister.mockResolvedValue(true);

    render(<RegisterForm onSuccess={mockOnSuccess} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "TestPassword123!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm Password"), {
      target: { value: "TestPassword123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it("shows login link when onSwitchToLogin is provided", () => {
    const mockOnSwitchToLogin = vi.fn();

    render(<RegisterForm onSwitchToLogin={mockOnSwitchToLogin} />);

    expect(screen.getByText("Already have an account?")).toBeInTheDocument();
    expect(screen.getByText("Login here")).toBeInTheDocument();
  });

  it("calls onSwitchToLogin when login link is clicked", () => {
    const mockOnSwitchToLogin = vi.fn();

    render(<RegisterForm onSwitchToLogin={mockOnSwitchToLogin} />);

    fireEvent.click(screen.getByText("Login here"));

    expect(mockOnSwitchToLogin).toHaveBeenCalled();
  });
});
