import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Add request deduplication to prevent duplicate requests
      staleTime: 1000, // Consider data fresh for 1 second
      gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes (renamed from cacheTime)
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  // Temporarily disable StrictMode to prevent double renders in development
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>
);
