import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import ChatInterface from "../../components/ChatInterface";
import { apiService } from "../../services/api";

// Mock the API service
vi.mock("../../services/api");
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

describe("ChatHistoryIntegration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it("maintains session across multiple turns", async () => {
    const sessionId = "test-session-123";
    const firstResponse = {
      answer: "First response",
      citations: [],
      session_id: sessionId,
      latency_ms: 100,
    };
    const secondResponse = {
      answer: "Second response",
      citations: [],
      session_id: sessionId,
      latency_ms: 100,
    };

    mockApiService.sendChatMessage
      .mockResolvedValueOnce(firstResponse)
      .mockResolvedValueOnce(secondResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    // First message
    await user.type(textarea, "First question");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(screen.getByText("First question")).toBeInTheDocument();
      expect(screen.getByText("First response")).toBeInTheDocument();
    });

    // Verify sessionId saved
    expect(localStorageMock.getItem("chat_session_id")).toBe(sessionId);

    // Second message - should use existing sessionId
    await user.type(textarea, "Second question");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        sessionId,
        "Second question"
      );
      expect(screen.getByText("Second question")).toBeInTheDocument();
      expect(screen.getByText("Second response")).toBeInTheDocument();
    });

    // Verify all messages are displayed
    expect(screen.getByText("First question")).toBeInTheDocument();
    expect(screen.getByText("First response")).toBeInTheDocument();
    expect(screen.getByText("Second question")).toBeInTheDocument();
    expect(screen.getByText("Second response")).toBeInTheDocument();
  });

  it("persists session across page reload simulation", async () => {
    const sessionId = "persistent-session-456";
    const response = {
      answer: "Response after reload",
      citations: [],
      session_id: sessionId,
      latency_ms: 100,
    };

    // First render - send message and get sessionId
    mockApiService.sendChatMessage.mockResolvedValueOnce({
      answer: "Initial response",
      citations: [],
      session_id: sessionId,
      latency_ms: 100,
    });

    const user = userEvent.setup();
    const { unmount } = renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "Initial message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(localStorageMock.getItem("chat_session_id")).toBe(sessionId);
    });

    // Simulate page reload - unmount and remount
    unmount();

    // Second render - should load sessionId from localStorage
    mockApiService.sendChatMessage.mockResolvedValueOnce(response);
    renderWithQueryClient(<ChatInterface />);

    // Verify sessionId was loaded
    const newTextarea = screen.getByPlaceholderText("Message...");
    const newButtons = screen.getAllByRole("button");
    const newSendButton = newButtons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(newTextarea, "Message after reload");
    await user.click(newSendButton!);

    await waitFor(() => {
      // Should use existing sessionId from localStorage
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        sessionId,
        "Message after reload"
      );
    });
  });

  it("creates new session when localStorage is empty", async () => {
    const newSessionId = "new-session-789";
    const response = {
      answer: "New session response",
      citations: [],
      session_id: newSessionId,
      latency_ms: 100,
    };

    mockApiService.sendChatMessage.mockResolvedValueOnce(response);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "New session message");
    await user.click(sendButton!);

    await waitFor(() => {
      // Should call with null for new session
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        null,
        "New session message"
      );
      // SessionId should be saved after response
      expect(localStorageMock.getItem("chat_session_id")).toBe(newSessionId);
    });
  });

  it("'New Conversation' creates new session on next message", async () => {
    const firstSessionId = "first-session-111";
    const secondSessionId = "second-session-222";

    mockApiService.sendChatMessage
      .mockResolvedValueOnce({
        answer: "First response",
        citations: [],
        session_id: firstSessionId,
        latency_ms: 100,
      })
      .mockResolvedValueOnce({
        answer: "Second response",
        citations: [],
        session_id: secondSessionId,
        latency_ms: 100,
      });

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    // Send first message
    await user.type(textarea, "First message");
    await user.click(sendButton!);

    await waitFor(() => {
      expect(localStorageMock.getItem("chat_session_id")).toBe(firstSessionId);
    });

    // Click "New Conversation"
    const newConversationButton = screen.getByText("New Conversation");
    await user.click(newConversationButton);

    // Verify session cleared
    expect(localStorageMock.getItem("chat_session_id")).toBeNull();

    // Send second message - should create new session
    await user.type(textarea, "Second message");
    await user.click(sendButton!);

    await waitFor(() => {
      // Should call with null to create new session
      expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
        null,
        "Second message"
      );
      // New sessionId should be saved
      expect(localStorageMock.getItem("chat_session_id")).toBe(secondSessionId);
    });
  });

  it("works without localStorage (backward compatibility)", async () => {
    // Mock localStorage to be unavailable
    const originalGetItem = localStorageMock.getItem;
    const originalSetItem = localStorageMock.setItem;
    localStorageMock.getItem = vi.fn(() => {
      throw new Error("localStorage unavailable");
    });
    localStorageMock.setItem = vi.fn(() => {
      throw new Error("localStorage unavailable");
    });

    const response = {
      answer: "Response without localStorage",
      citations: [],
      session_id: "session-without-storage",
      latency_ms: 100,
    };

    mockApiService.sendChatMessage.mockResolvedValueOnce(response);

    const user = userEvent.setup();
    renderWithQueryClient(<ChatInterface />);

    const textarea = screen.getByPlaceholderText("Message...");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons.find((btn) =>
      btn.getAttribute("aria-label")?.includes("Send")
    );

    await user.type(textarea, "Test message");
    await user.click(sendButton!);

    // App should continue to function
    await waitFor(() => {
      expect(screen.getByText("Test message")).toBeInTheDocument();
      expect(
        screen.getByText("Response without localStorage")
      ).toBeInTheDocument();
    });

    // Restore original functions
    localStorageMock.getItem = originalGetItem;
    localStorageMock.setItem = originalSetItem;
  });
});
