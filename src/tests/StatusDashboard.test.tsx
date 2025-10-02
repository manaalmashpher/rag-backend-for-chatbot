import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import StatusDashboard from "../components/StatusDashboard";
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

const mockStatusData = {
  id: "ing_123",
  status: "processing" as const,
  blocked_reason: null,
  created_at: "2025-01-12T10:00:00Z",
};

describe("StatusDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows no ingestion selected message when no ingestionId provided", () => {
    renderWithQueryClient(<StatusDashboard />);

    expect(screen.getByText("No Ingestion Selected")).toBeInTheDocument();
    expect(
      screen.getByText(/enter an ingestion id to view its status/i)
    ).toBeInTheDocument();
  });

  it("shows loading state when fetching status", () => {
    mockApiService.getIngestionStatus.mockImplementation(
      () =>
        new Promise((resolve) => setTimeout(() => resolve(mockStatusData), 100))
    );

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    expect(screen.getByText("Loading status...")).toBeInTheDocument();
  });

  it("displays status information when data is loaded", async () => {
    mockApiService.getIngestionStatus.mockResolvedValue(mockStatusData);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Ingestion Status")).toBeInTheDocument();
      expect(screen.getByText("ID: ing_123")).toBeInTheDocument();
      expect(screen.getByText("Processing")).toBeInTheDocument();
      expect(
        screen.getByText("Extracting text and preparing chunks")
      ).toBeInTheDocument();
    });

    // Check ingestion info
    expect(screen.getByText("Ingestion ID")).toBeInTheDocument();
    expect(screen.getByText("ing_123")).toBeInTheDocument();
  });

  it("shows completed status correctly", async () => {
    const completedStatus = {
      ...mockStatusData,
      status: "completed" as const,
    };
    mockApiService.getIngestionStatus.mockResolvedValue(completedStatus);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Completed")).toBeInTheDocument();
      expect(
        screen.getByText("Document processing completed successfully")
      ).toBeInTheDocument();
    });
  });

  it("shows failed status with error", async () => {
    const failedStatus = {
      ...mockStatusData,
      status: "failed" as const,
      error: "Processing error occurred",
    };
    mockApiService.getIngestionStatus.mockResolvedValue(failedStatus);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Failed")).toBeInTheDocument();
      expect(
        screen.getByText("Document processing failed")
      ).toBeInTheDocument();
    });

    // Check error is displayed
    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.getByText("Processing error occurred")).toBeInTheDocument();
  });

  it("shows blocked reason when present", async () => {
    const blockedStatus = {
      ...mockStatusData,
      status: "pending" as const,
      blocked_reason: "File size exceeds limit",
    };
    mockApiService.getIngestionStatus.mockResolvedValue(blockedStatus);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Blocked Reason")).toBeInTheDocument();
      expect(screen.getByText("File size exceeds limit")).toBeInTheDocument();
    });
  });

  it("shows error message when API call fails", async () => {
    const mockError = new Error("Failed to fetch status");
    mockApiService.getIngestionStatus.mockRejectedValue(mockError);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Error Loading Status")).toBeInTheDocument();
      expect(screen.getByText("Failed to fetch status")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /try again/i })
      ).toBeInTheDocument();
    });
  });

  it("shows not found message for invalid ingestion ID", async () => {
    mockApiService.getIngestionStatus.mockResolvedValue(null as any);

    renderWithQueryClient(<StatusDashboard ingestionId="invalid_id" />);

    await waitFor(() => {
      expect(screen.getByText("Status Not Found")).toBeInTheDocument();
      expect(
        screen.getByText(/no status found for ingestion id: invalid_id/i)
      ).toBeInTheDocument();
    });
  });

  it("refreshes data when refresh button is clicked", async () => {
    mockApiService.getIngestionStatus.mockResolvedValue(mockStatusData);

    const user = userEvent.setup();
    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Processing")).toBeInTheDocument();
    });

    const refreshButton = screen.getByRole("button", { name: /refresh/i });
    await user.click(refreshButton);

    expect(mockApiService.getIngestionStatus).toHaveBeenCalledTimes(2);
  });

  it("shows progress indicator for processing status", async () => {
    mockApiService.getIngestionStatus.mockResolvedValue(mockStatusData);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Processing Progress")).toBeInTheDocument();
      expect(screen.getByText("In progress...")).toBeInTheDocument();
    });
  });

  it("does not show progress indicator for completed status", async () => {
    const completedStatus = {
      ...mockStatusData,
      status: "completed" as const,
    };
    mockApiService.getIngestionStatus.mockResolvedValue(completedStatus);

    renderWithQueryClient(<StatusDashboard ingestionId="ing_123" />);

    await waitFor(() => {
      expect(screen.getByText("Completed")).toBeInTheDocument();
    });

    expect(screen.queryByText("Processing Progress")).not.toBeInTheDocument();
  });
});
