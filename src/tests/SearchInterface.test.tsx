import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import SearchInterface from "../components/SearchInterface";
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

const mockSearchResponse = {
  params: {
    topk_vec: 20,
    topk_lex: 20,
    w_sem: 0.6,
    w_lex: 0.4,
  },
  latency_ms: 150,
  results: [
    {
      doc_id: "doc_123",
      chunk_id: "ch_001",
      method: 1,
      page_from: 1,
      page_to: 2,
      snippet: "This is a test snippet with search query in it.",
      score: 0.85,
    },
    {
      doc_id: "doc_456",
      chunk_id: "ch_002",
      method: 2,
      page_from: 3,
      page_to: 4,
      snippet: "Another test snippet for the search results.",
      score: 0.72,
    },
  ],
};

describe("SearchInterface", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders search form with input and button", () => {
    renderWithQueryClient(<SearchInterface />);

    expect(screen.getByLabelText("Search Documents")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument();
  });

  it("shows search tips when no query is entered", () => {
    renderWithQueryClient(<SearchInterface />);

    expect(screen.getByText("Search Tips")).toBeInTheDocument();
    expect(
      screen.getByText(/use natural language queries/i)
    ).toBeInTheDocument();
  });

  it("disables search button when query is empty", () => {
    renderWithQueryClient(<SearchInterface />);

    const searchButton = screen.getByRole("button", { name: /search/i });
    expect(searchButton).toBeDisabled();
  });

  it("enables search button when query is entered", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    expect(searchButton).toBeEnabled();
  });

  it("calls search API when form is submitted", async () => {
    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(() => {
      expect(mockApiService.searchDocuments).toHaveBeenCalledWith("test query");
    });
  });

  it("displays search results when API returns data", async () => {
    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("Search Results")).toBeInTheDocument();
      expect(screen.getByText("2 results found")).toBeInTheDocument();
      expect(screen.getByText("(150ms)")).toBeInTheDocument();
    });

    // Check that results are displayed
    expect(screen.getByText("Score: 85.0%")).toBeInTheDocument();
    expect(screen.getByText("Score: 72.0%")).toBeInTheDocument();
    expect(
      screen.getByText("This is a test snippet with search query in it.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Another test snippet for the search results.")
    ).toBeInTheDocument();
  });

  it("highlights search query in results", async () => {
    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test");
    await user.click(searchButton);

    await waitFor(() => {
      // Look for the mark element with the highlight class
      const markElement = document.querySelector("mark.bg-yellow-200");
      expect(markElement).toBeInTheDocument();
      expect(markElement).toHaveTextContent("test");
    });
  });

  it("displays search parameters", async () => {
    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("Search Parameters")).toBeInTheDocument();
      // The component shows different parameter structure than what's in the mock
      expect(screen.getByText("Total Results:")).toBeInTheDocument();
      expect(screen.getByText("Search Type:")).toBeInTheDocument();
    });
  });

  it("shows loading state during search", async () => {
    // Mock a delayed response
    mockApiService.searchDocuments.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve(mockSearchResponse), 100)
        )
    );

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    expect(screen.getByText("Searching documents...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /searching/i })).toBeDisabled();
  });

  it("shows error message when search fails", async () => {
    const mockError = new Error("Search failed");
    mockApiService.searchDocuments.mockRejectedValue(mockError);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(
      () => {
        expect(screen.getByText("Search Error")).toBeInTheDocument();
        expect(screen.getByText("Search failed")).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /try again/i })
        ).toBeInTheDocument();
      },
      { timeout: 10000 }
    );
  });

  it("shows no results message when API returns empty results", async () => {
    const emptyResponse = {
      ...mockSearchResponse,
      results: [],
    };
    mockApiService.searchDocuments.mockResolvedValue(emptyResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("No Results Found")).toBeInTheDocument();
      expect(screen.getByText(/try different keywords/i)).toBeInTheDocument();
    });
  });

  it("clears search when clear button is clicked", async () => {
    mockApiService.searchDocuments.mockResolvedValue(mockSearchResponse);

    const user = userEvent.setup();
    renderWithQueryClient(<SearchInterface />);

    const searchInput = screen.getByLabelText("Search Documents");
    const searchButton = screen.getByRole("button", { name: /search/i });

    await user.type(searchInput, "test query");
    await user.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("Search Results")).toBeInTheDocument();
    });

    const clearButton = screen.getByRole("button", { name: /clear/i });
    await user.click(clearButton);

    expect(searchInput).toHaveValue("");
    expect(screen.queryByText("Search Results")).not.toBeInTheDocument();
  });

  it("initializes with provided initial query", () => {
    renderWithQueryClient(<SearchInterface initialQuery="initial test" />);

    const searchInput = screen.getByLabelText("Search Documents");
    expect(searchInput).toHaveValue("initial test");
  });
});
