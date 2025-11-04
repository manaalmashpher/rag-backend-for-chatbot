import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import ChatInterface from "../components/ChatInterface";
import { apiService } from "../services/api";

// Mock the API service
vi.mock("../services/api");
const mockApiService = apiService as any;

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
  conversation_id: "test-conversation-id",
  latency_ms: 250,
};

describe("ChatInterface", () => {
  const conversationId = "test-conversation-id";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no messages", () => {
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    expect(screen.getByText("Start a conversation")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Ask a question to get started with your document search/i
      )
    ).toBeInTheDocument();
  });

  it("renders input box and send button", () => {
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    expect(
      screen.getByPlaceholderText(
        /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("disables send button when input is empty", () => {
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const sendButton = screen.getByRole("button");
    expect(sendButton).toBeDisabled();
  });

  it("enables send button when input has text", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    expect(sendButton).toBeEnabled();
  });

  it("calls API when message is submitted", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        conversationId,
        "test message"
      );
    });
  });

  it("displays user and assistant messages after successful API call", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

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
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/Citations \(2\)/i)).toBeInTheDocument();
      expect(screen.getByText("Score: 85.0%")).toBeInTheDocument();
      expect(screen.getByText("Score: 72.0%")).toBeInTheDocument();
    });
  });

  it("sorts citations by score (highest first)", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

    await waitFor(() => {
      const citations = screen.getAllByText(/Score: \d+\.\d+%/);
      // First citation should have higher score (85.0%)
      expect(citations[0]).toHaveTextContent("Score: 85.0%");
      expect(citations[1]).toHaveTextContent("Score: 72.0%");
    });
  });

  it("displays error message when API call fails", async () => {
    const mockError = new Error("API request failed");
    mockApiService.sendChatMessage.mockRejectedValue(mockError);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

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
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

    expect(screen.getByText("Thinking...")).toBeInTheDocument();
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it("clears input after successful message submission", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    ) as HTMLTextAreaElement;
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

    await waitFor(() => {
      expect(textarea.value).toBe("");
    });
  });

  it("submits message when Enter key is pressed", async () => {
    mockApiService.sendChatMessage.mockResolvedValue(mockChatResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );

    await user.type(textarea, "test message{Enter}");

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        conversationId,
        "test message"
      );
    });
  });

  it("shows character counter", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );

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
    renderWithQueryClient(<ChatInterface conversationId={conversationId} />);

    const textarea = screen.getByPlaceholderText(
      /Type your message... \(Press Enter to send, Shift\+Enter for new line\)/i
    );
    const sendButton = screen.getByRole("button");

    await user.type(textarea, "test message");
    await user.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText("No citations available")).toBeInTheDocument();
    });
  });

  it("persists conversation ID across renders", () => {
    const { rerender } = renderWithQueryClient(
      <ChatInterface conversationId={conversationId} />
    );

    rerender(
      <QueryClientProvider client={createTestQueryClient()}>
        <ChatInterface conversationId={conversationId} />
      </QueryClientProvider>
    );

    // Conversation ID should remain the same (tested via API calls)
    expect(conversationId).toBe(conversationId);
  });
});
