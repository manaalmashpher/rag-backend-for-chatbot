import React from "react";
import { render, screen, waitFor, within, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import App from "../../App";
import { apiService } from "../../services/api";

// Mock the API service
vi.mock("../../services/api");
const mockApiService = apiService as any;

// Mock the auth service
vi.mock("../../services/auth", () => ({
  authService: {
    getCurrentUser: vi.fn().mockResolvedValue({
      id: 1,
      email: "test@example.com",
      organization_id: 1,
      is_active: true,
    }),
    login: vi.fn().mockResolvedValue(true),
    logout: vi.fn(),
  },
}));

// Mock the AuthContext to provide an authenticated user
vi.mock("../../contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
    user: {
      id: 1,
      email: "test@example.com",
      organization_id: 1,
      is_active: true,
    },
    isAuthenticated: true,
    isLoading: false,
    error: null,
    login: vi.fn().mockResolvedValue(true),
    register: vi.fn().mockResolvedValue(true),
    logout: vi.fn(),
    clearError: vi.fn(),
  }),
}));

// Mock the ProtectedRoute to always render children
vi.mock("../../components/auth/ProtectedRoute", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => children,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderApp = (initialRoute = "/") => {
  const queryClient = createTestQueryClient();
  let result: any;

  act(() => {
    result = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialRoute]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>
    );
  });

  return result;
};

describe("Upload to Search Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("allows user to upload document and then search for it", async () => {
    const mockUploadResponse = {
      doc_id: "doc_123",
      ingestion_id: "ing_123",
    };

    const mockStatusResponse = {
      id: "ing_123",
      status: "completed" as const,
      blocked_reason: null,
      created_at: "2025-01-12T10:00:00Z",
    };

    const mockSearchResponse = {
      params: {
        topk_vec: 20,
        topk_lex: 20,
        w_sem: 0.6,
        w_lex: 0.4,
      },
      latency_ms: 100,
      results: [
        {
          doc_id: "doc_123",
          chunk_id: "ch_001",
          method: 1,
          page_from: 1,
          page_to: 2,
          snippet: "This is the content from the uploaded document.",
          score: 0.95,
        },
      ],
    };

    // Mock API responses
    mockApiService.uploadDocument.mockResolvedValue(mockUploadResponse);
    mockApiService.getIngestionStatus.mockResolvedValue(mockStatusResponse);
    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderApp("/upload"); // Start at upload page

    // Navigate to upload page - target the main navigation link specifically
    const uploadLink = within(screen.getByRole("navigation")).getByRole(
      "link",
      { name: /^upload$/i }
    );
    await act(async () => {
      await user.click(uploadLink);
    });

    expect(screen.getByText("Upload Documents")).toBeInTheDocument();

    // Fill upload form
    const titleInput = screen.getByLabelText("Document Title");
    await user.type(titleInput, "Test Document");

    // Mock file selection
    const file = new File(
      ["This is test content for the document."],
      "test.pdf",
      {
        type: "application/pdf",
      }
    );
    const fileInput = screen
      .getByLabelText("Select Document")
      .parentElement?.querySelector("input");

    if (fileInput) {
      await user.upload(fileInput, file);
    }

    // Submit upload
    const uploadButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    await act(async () => {
      await user.click(uploadButton);
    });

    // Wait for upload success
    await waitFor(
      () => {
        expect(
          screen.getByText(/document uploaded successfully/i)
        ).toBeInTheDocument();
      },
      { timeout: 15000 }
    );

    // Navigate to status page
    const statusLink = within(screen.getByRole("navigation")).getByRole(
      "link",
      { name: /^status$/i }
    );
    await act(async () => {
      await user.click(statusLink);
    });

    expect(screen.getByText("Ingestion Status")).toBeInTheDocument();

    // Check status
    const statusInput = screen.getByLabelText("Ingestion ID");
    await user.type(statusInput, "ing_123");

    const viewStatusButton = screen.getByRole("button", {
      name: /view status/i,
    });
    await act(async () => {
      await user.click(viewStatusButton);
    });

    await waitFor(
      () => {
        expect(screen.getByText("Completed")).toBeInTheDocument();
      },
      { timeout: 15000 }
    );

    // Navigate to search page
    const searchLink = within(screen.getByRole("navigation")).getByRole(
      "link",
      { name: /^search$/i }
    );
    await act(async () => {
      await user.click(searchLink);
    });

    expect(
      screen.getByRole("heading", { name: "Search Documents" })
    ).toBeInTheDocument();

    // Perform search
    const searchInput = screen.getByLabelText("Search Documents");
    await user.type(searchInput, "test content");

    const searchButton = screen.getByRole("button", { name: /search/i });
    await act(async () => {
      await user.click(searchButton);
    });

    // Wait for search results
    await waitFor(
      () => {
        expect(screen.getByText("Search Results")).toBeInTheDocument();
        expect(screen.getByText("1 results found")).toBeInTheDocument();
      },
      { timeout: 15000 }
    );

    // Verify search results
    expect(
      screen.getByText("This is the content from the uploaded document.")
    ).toBeInTheDocument();
    expect(screen.getByText("Score: 95.0%")).toBeInTheDocument();
  });

  it("handles upload error gracefully", async () => {
    const mockError = new Error("Upload failed");
    mockApiService.uploadDocument.mockRejectedValue(mockError);

    const user = userEvent.setup();
    renderApp("/upload"); // Start at upload page

    // Fill upload form directly since we're already on upload page
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

    // Submit upload
    const uploadButton = screen.getByRole("button", {
      name: /upload document/i,
    });
    await act(async () => {
      await user.click(uploadButton);
    });

    // Wait for error message - be more specific about what we're looking for
    await waitFor(
      () => {
        expect(screen.getByText("Upload failed")).toBeInTheDocument();
      },
      { timeout: 15000 }
    );
  });

  it("handles search error gracefully", async () => {
    const mockError = new Error("Search failed");
    mockApiService.searchDocuments.mockRejectedValue(mockError);

    const user = userEvent.setup();

    await act(async () => {
      renderApp("/search"); // Start at search page
    });

    // Perform search directly since we're already on search page
    const searchInput = screen.getByLabelText("Search Documents");
    await user.clear(searchInput);
    await user.type(searchInput, "test query");

    const searchButton = screen.getByRole("button", { name: /search/i });
    await act(async () => {
      await user.click(searchButton);
    });

    // Wait for error message - be more specific about what we're looking for
    await waitFor(
      () => {
        expect(screen.getByText("Search Error")).toBeInTheDocument();
        expect(screen.getByText("Search failed")).toBeInTheDocument();
      },
      { timeout: 15000 }
    );
  });

  it("maintains navigation state across pages", async () => {
    const user = userEvent.setup();
    renderApp("/"); // Start at home page

    // Start at home page - wait longer and check for any text that indicates home page
    await waitFor(
      () => {
        expect(screen.getByText("Welcome to IonologyBot")).toBeInTheDocument();
      },
      { timeout: 15000 }
    );

    // Navigate to upload
    const uploadLink = within(screen.getByRole("navigation")).getByRole(
      "link",
      { name: /^upload$/i }
    );
    await act(async () => {
      await user.click(uploadLink);
    });
    expect(screen.getByText("Upload Documents")).toBeInTheDocument();

    // Navigate to status
    const statusLink = within(screen.getByRole("navigation")).getByRole(
      "link",
      { name: /^status$/i }
    );
    await act(async () => {
      await user.click(statusLink);
    });
    expect(screen.getByText("Ingestion Status")).toBeInTheDocument();

    // Navigate to search
    const searchLink = within(screen.getByRole("navigation")).getByRole(
      "link",
      { name: /^search$/i }
    );
    await act(async () => {
      await user.click(searchLink);
    });
    expect(
      screen.getByRole("heading", { name: "Search Documents" })
    ).toBeInTheDocument();

    // Navigate back to home
    const homeLink = within(screen.getByRole("navigation")).getByRole("link", {
      name: /^home$/i,
    });
    await act(async () => {
      await user.click(homeLink);
    });
    expect(screen.getByText("Welcome to IonologyBot")).toBeInTheDocument();
  });
});
