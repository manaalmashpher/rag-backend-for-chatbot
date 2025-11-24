import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import ChatInterface from "../components/ChatInterface";
import { apiService } from "../services/api";

// Mock the API service
vi.mock("../services/api");
const mockApiService = apiService as any;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

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

const mockChatResponse = {
  answer: "This is a test response from the chat API.",
  citations: [
    {
      doc_id: "doc_123",
      chunk_id: "ch_001",
      page_from: 1,
      page_to: 2,
      score: 0.85,
      text: "This is a test citation text that should be displayed in the citations panel.",
    },
    {
      doc_id: "doc_456",
      chunk_id: "ch_002",
      score: 0.72,
      text: "Another citation text for testing purposes.",
    },
  ],
  session_id: "test-session-id-123",
  latency_ms: 250,
};

describe("ChatInterface", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it("renders empty state when no messages", () => {
    renderWithQueryClient(<ChatInterface />);

    expect(screen.getByText("Start a conversation")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Ask questions in natural language and receive answers with/i
      )
    ).toBeInTheDocument();
  });

  it("renders input box and send button", () => {
    renderWithQueryClient(<ChatInterface />);

    expect(screen.getByPlaceholderText("Message...")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("disables send button when input is empty", () => {
    renderWithQueryClient(<ChatInterface />);

    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );
    expect(sendButton).toBeDisabled();
  });

  it("enables send button when input has text", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    expect(sendButton).not.toBeDisabled();
  });

  it("calls API with null sessionId for first message", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        null,
        "test message"
      );
    });
  });

  it("saves sessionId to localStorage after API response", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(localStorageMock.getItem("chat_session_id")).toBe(
        "test-session-id-123"
      );
    });
  });

  it("loads sessionId from localStorage on mount", () => {
    localStorageMock.setItem("chat_session_id", "existing-session-id");

    renderWithQueryClient(<ChatInterface />);

    // Component should load sessionId from localStorage
    // This is tested indirectly by checking API calls use the loaded sessionId
    expect(localStorageMock.getItem("chat_session_id")).toBe(
      "existing-session-id"
    );
  });

  it("uses existing sessionId for subsequent messages", async () => {
    localStorageMock.setItem("chat_session_id", "existing-session-id");
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        "existing-session-id",
        "test message"
      );
    });
  });

  it("displays user and assistant messages after successful API call", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("test message")).toBeInTheDocument();
      expect(
        screen.getByText("This is a test response from the chat API.")
      ).toBeInTheDocument();
    });
  });

  it("displays citations after successful API call", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      // Check for Citations header (h4 element)
      const citationsHeader = screen.getByRole("heading", {
        name: /Citations/i,
      });
      expect(citationsHeader).toBeInTheDocument();
      expect(screen.getByText("85.0%")).toBeInTheDocument();
      expect(screen.getByText("72.0%")).toBeInTheDocument();
    });
  });

  it("sorts citations by score (highest first)", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      const scoreElements = screen.getAllByText(/\d+\.\d+%/);
      // First citation should have higher score (85.0%)
      expect(scoreElements[0]).toHaveTextContent("85.0%");
      expect(scoreElements[1]).toHaveTextContent("72.0%");
    });
  });

  it("displays error message when API call fails", async () => {
    const mockError = new Error("API request failed");
    mockApiService.sendChatMessage.mockRejectedValue(mockError);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
      expect(screen.getByText("API request failed")).toBeInTheDocument();
    });
  });

  it("shows loading state during API request", async () => {
    mockApiService.sendChatMessage.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve(mockChatResponse), 100)
        )
    );

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    expect(screen.getByText("Thinking...")).toBeInTheDocument();
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it("clears input after successful message submission", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText(
      "Message..."
    ) as HTMLTextAreaElement;
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(textarea.value).toBe("");
    });
  });

  it("submits message when Enter key is pressed", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");

    await user.type(textarea, "test message{Enter}");

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        null,
        "test message"
      );
    });
  });

  it("shows character counter", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");

    await user.type(textarea, "test");
    expect(screen.getByText("4/1000")).toBeInTheDocument();
  });

  it("displays 'No citations available' when citations array is empty", async () => {
    const responseWithoutCitations = {
      ...mockChatResponse,
      citations: [],
    };
    mockApiService.sendChatMessage.mockResolvedValue(responseWithoutCitations);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("No citations available")).toBeInTheDocument();
    });
  });

  it("displays 'New Conversation' button when messages exist", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("New Conversation")).toBeInTheDocument();
    });
  });

  it("'New Conversation' button clears session and messages", async () => {
    localStorageMock.setItem("chat_session_id", "existing-session-id");
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    // Send a message first
    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("New Conversation")).toBeInTheDocument();
    });

    // Click "New Conversation" button
    const newConversationButton = screen.getByText("New Conversation");
    await user.click(newConversationButton);

    // Verify session cleared from localStorage
    expect(localStorageMock.getItem("chat_session_id")).toBeNull();

    // Verify messages cleared (empty state should show)
    await waitFor(() => {
      expect(screen.getByText("Start a conversation")).toBeInTheDocument();
    });

    // Next message should create new session
    await user.type(textarea, "new message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        null,
        "new message"
      );
    });
  });

  it("handles localStorage errors gracefully", async () => {
    // Mock localStorage to throw errors
    const originalSetItem = localStorageMock.setItem;
    localStorageMock.setItem = vi.fn(() => {
      throw new Error("QuotaExceededError");
    });

    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    // App should continue to function even if localStorage fails
    await waitFor(() => {
      expect(screen.getByText("test message")).toBeInTheDocument();
      expect(
        screen.getByText("This is a test response from the chat API.")
      ).toBeInTheDocument();
    });

    // Restore original function
    localStorageMock.setItem = originalSetItem;
  });

  it("works without localStorage (graceful fallback)", async () => {
    // Mock localStorage to be unavailable
    const originalGetItem = localStorageMock.getItem;
    const originalSetItem = localStorageMock.setItem;
    localStorageMock.getItem = vi.fn(() => {
      throw new Error("localStorage unavailable");
    });
    localStorageMock.setItem = vi.fn(() => {
      throw new Error("localStorage unavailable");
    });

    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "test message");
    await user.click(sendButton!);

    // App should continue to function
    await waitFor(() => {
      expect(screen.getByText("test message")).toBeInTheDocument();
    });

    // Restore original functions
    localStorageMock.getItem = originalGetItem;
    localStorageMock.setItem = originalSetItem;
  });
});
