import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const mockChatResponse = {
  answer: "This is a test response from the chat API.",
  citations: [
    {
      doc_id: "doc_123",
      chunk_id: "ch_001",
      page_from: 1,
      page_to: 2,
      score: 0.85,
      text: "This is a test citation text.",
    },
  ],
  conversation_id: "test-conversation-id",
  latency_ms: 250,
};

describe("Chat Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // INT-001: ChatPage route accessible at /chat
  it("renders ChatPage when navigating to /chat route", () => {
    renderApp("/chat");

    expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument();
    expect(
      screen.getByText(
        /Ask questions in natural language and receive answers with citations/i
      )
    ).toBeInTheDocument();
  });

  // INT-002: ChatPage protected by ProtectedRoute
  it("ChatPage is accessible through ProtectedRoute (mocked to always allow)", () => {
    renderApp("/chat");

    // If ProtectedRoute blocks access, we wouldn't see the Chat content
    // Since we mock it to always allow, we can verify the page renders
    expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument();
  });

  // INT-023: SearchPage route still accessible
  it("SearchPage route still accessible at /search", () => {
    renderApp("/search");

    // Verify SearchPage renders (check for search-specific content)
    expect(screen.getByLabelText(/search/i)).toBeInTheDocument();
  });

  // INT-024: SearchPage functionality unchanged
  it("SearchPage functionality remains unchanged", async () => {
    const mockSearchResponse = {
      results: [
        {
          chunk_id: "ch_001",
          doc_id: "doc_123",
          method: 1,
          score: 0.85,
          search_type: "hybrid",
          snippet: "Test search result",
        },
      ],
      total_results: 1,
      query: "test query",
      limit: 10,
      search_type: "hybrid",
      latency_ms: 100,
    };

    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderApp("/search");

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(() => {
      expect(mockApiService.searchDocuments).toHaveBeenCalledWith("test query");
      expect(screen.getByText("Search Results")).toBeInTheDocument();
    });
  });

  // INT-012: useMutation hook calls API correctly
  it("useMutation hook calls sendChatMessage API correctly", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalled();
    });
  });

  // INT-013: API request includes conversation_id
  it("API request includes conversation_id in request payload", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalled();
      const callArgs = mockApiService.sendChatMessage.mock.calls[0];
      expect(callArgs).toHaveLength(2);
      expect(callArgs[0]).toBeTruthy(); // conversation_id should be a string
      expect(typeof callArgs[0]).toBe("string");
      expect(callArgs[1]).toBe("test message");
    });
  });

  // INT-014: API request includes message
  it("API request includes message in request payload", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    const testMessage = "What is the document about?";
    await user.type(textarea, testMessage);
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        expect.any(String),
        testMessage
      );
    });
  });

  // INT-010: Conversation ID sent in API requests
  it("Conversation ID is sent in API requests and persists across messages", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    // Send first message
    await user.type(textarea, "first message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledTimes(1);
    });

    const firstCallConversationId =
      mockApiService.sendChatMessage.mock.calls[0][0];
    expect(firstCallConversationId).toBeTruthy();
    expect(typeof firstCallConversationId).toBe("string");

    // Wait for first message to complete, then send second message
    await waitFor(() => {
      expect(screen.getByText("first message")).toBeInTheDocument();
    });

    // Find textarea again after re-render
    const textarea2 = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form2 = textarea2.closest("form");
    const sendButton2 = form2?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    await user.type(textarea2, "second message");
    await user.click(sendButton2!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledTimes(2);
    });

    const secondCallConversationId =
      mockApiService.sendChatMessage.mock.calls[1][0];
    // Conversation ID should be the same across calls
    expect(secondCallConversationId).toBe(firstCallConversationId);
  });

  // INT-015: Network error displays user message
  it("displays user-friendly error message when network error occurs", async () => {
    const networkError = new Error("Network Error");
    networkError.name = "NetworkError";
    mockApiService.sendChatMessage.mockRejectedValue(networkError);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
      // Should show error message (either from API or fallback)
      expect(
        screen.getByText(/Failed to send message|Network Error/i)
      ).toBeInTheDocument();
    });
  });

  // INT-016: API 400 error displays user message
  it("displays user-friendly error message when API returns 400 error", async () => {
    const apiError: any = new Error(
      "Message must be between 1 and 1000 characters"
    );
    apiError.response = {
      data: {
        error: {
          code: "VALIDATION_ERROR",
          message: "Message must be between 1 and 1000 characters",
          details: {},
          requestId: "req-123",
        },
      },
      status: 400,
    };
    mockApiService.sendChatMessage.mockRejectedValue(apiError);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
      expect(
        screen.getByText(/Message must be between 1 and 1000 characters/i)
      ).toBeInTheDocument();
    });
  });

  // INT-017: API 500 error displays user message
  it("displays user-friendly error message when API returns 500 error", async () => {
    const apiError: any = new Error(
      "An error occurred while processing your request"
    );
    apiError.response = {
      data: {
        error: {
          code: "CHAT_ERROR",
          message: "An error occurred while processing your request",
          details: {},
          requestId: "req-456",
        },
      },
      status: 500,
    };
    mockApiService.sendChatMessage.mockRejectedValue(apiError);

    const user = userEvent.setup();
    renderApp("/chat");

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const form = textarea.closest("form");
    const sendButton = form?.querySelector(
      "button[type='submit']"
    ) as HTMLButtonElement;

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
      expect(
        screen.getByText(/An error occurred while processing your request/i)
      ).toBeInTheDocument();
    });
  });
});
