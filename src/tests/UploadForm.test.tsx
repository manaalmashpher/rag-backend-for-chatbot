import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import UploadForm from "../components/UploadForm";
import { apiService } from "../services/api";

// Mock the API service
vi.mock("../services/api");
const mockApiService = apiService as any;

// Mock react-dropzone with proper file handling
vi.mock("react-dropzone", () => ({
  useDropzone: ({ onDrop }: any) => ({
    getRootProps: () => ({
      onClick: vi.fn(),
      onKeyDown: vi.fn(),
      role: "button",
      tabIndex: 0,
    }),
    getInputProps: () => ({
      onChange: (e: any) => {
        if (e.target.files && e.target.files[0]) {
          onDrop([e.target.files[0]], []);
        }
      },
      accept:
        "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown",
      multiple: false,
    }),
    isDragActive: false,
  }),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
};

describe("UploadForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders upload form with all required fields", () => {
    renderWithQueryClient(<UploadForm />);

    expect(screen.getByText("Select Document")).toBeInTheDocument();
    expect(screen.getByText("Document Title")).toBeInTheDocument();
    expect(screen.getByText("Chunking Method")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /upload document/i })
    ).toBeInTheDocument();
  });

  it("displays drag and drop area", () => {
    renderWithQueryClient(<UploadForm />);

    expect(
      screen.getByText(/drag & drop a file here, or click to select/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/pdf, docx, txt, or md files up to 20mb/i)
    ).toBeInTheDocument();
  });

  it("shows all chunking method options", () => {
    renderWithQueryClient(<UploadForm />);

    const select = screen.getByLabelText("Chunking Method");
    expect(select).toBeInTheDocument();

    // Check that all 8 chunking methods are available
    for (let i = 1; i <= 8; i++) {
      expect(screen.getByText(new RegExp(`Method ${i}:`))).toBeInTheDocument();
    }
  });

  it("validates required fields before submission", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<UploadForm />);

    const submitButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    expect(submitButton).toBeDisabled();

    // Fill in document title
    const titleInput = screen.getByLabelText("Document Title");
    await user.type(titleInput, "Test Document");

    // Still disabled without file
    expect(submitButton).toBeDisabled();
  });

  it("calls onUploadSuccess when upload succeeds", async () => {
    const mockOnUploadSuccess = vi.fn();
    const mockResponse = {
      doc_id: "doc_123",
      ingestion_id: "ing_123",
    };

    mockApiService.uploadDocument.mockResolvedValue(mockResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<UploadForm onUploadSuccess={mockOnUploadSuccess} />);

    // Fill in form
    const titleInput = screen.getByLabelText("Document Title");
    await user.type(titleInput, "Test Document");

    // Mock file selection
    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });
    const fileInput = screen
      .getByLabelText("Select Document")
      .parentElement?.querySelector("input");

    if (fileInput) {
      await user.upload(fileInput, file);
    }

    // Submit form
    const submitButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockApiService.uploadDocument).toHaveBeenCalledWith(
        file,
        "Test Document",
        1
      );
      expect(mockOnUploadSuccess).toHaveBeenCalledWith(mockResponse);
    });
  });

  it("calls onUploadError when upload fails", async () => {
    const mockOnUploadError = vi.fn();
    const mockError = new Error("Upload failed");

    mockApiService.uploadDocument.mockRejectedValue(mockError);

    const user = userEvent.setup();
    renderWithQueryClient(<UploadForm onUploadError={mockOnUploadError} />);

    // Fill in form
    const titleInput = screen.getByLabelText("Document Title");
    await user.type(titleInput, "Test Document");

    // Mock file selection
    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });
    const fileInput = screen
      .getByLabelText("Select Document")
      .parentElement?.querySelector("input");

    if (fileInput) {
      await user.upload(fileInput, file);
    }

    // Submit form
    const submitButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalledWith("Upload failed");
    });
  });

  it("shows success message after successful upload", async () => {
    const mockResponse = {
      doc_id: "doc_123",
      ingestion_id: "ing_123",
    };

    mockApiService.uploadDocument.mockResolvedValue(mockResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<UploadForm />);

    // Fill in form
    const titleInput = screen.getByLabelText("Document Title");
    await user.type(titleInput, "Test Document");

    // Mock file selection
    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });
    const fileInput = screen
      .getByLabelText("Select Document")
      .parentElement?.querySelector("input");

    if (fileInput) {
      await user.upload(fileInput, file);
    }

    // Submit form
    const submitButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          /Document uploaded successfully! Processing has started/i
        )
      ).toBeInTheDocument();
    });
  });

  it("resets form after successful upload", async () => {
    const mockResponse = {
      doc_id: "doc_123",
      ingestion_id: "ing_123",
    };

    mockApiService.uploadDocument.mockResolvedValue(mockResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<UploadForm />);

    // Fill in form
    const titleInput = screen.getByLabelText("Document Title");
    await user.type(titleInput, "Test Document");

    // Mock file selection
    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });
    const fileInput = screen
      .getByLabelText("Select Document")
      .parentElement?.querySelector("input");

    if (fileInput) {
      await user.upload(fileInput, file);
    }

    // Submit form
    const submitButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    await user.click(submitButton);

    // Wait for success message and then for form reset
    await waitFor(() => {
      expect(
        screen.getByText(
          /Document uploaded successfully! Processing has started/i
        )
      ).toBeInTheDocument();
    });

    // Wait for form reset (3 seconds timeout)
    await waitFor(
      () => {
        expect(titleInput).toHaveValue("");
      },
      { timeout: 4000 }
    );
  });
});
