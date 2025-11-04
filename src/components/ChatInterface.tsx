import React, { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, AlertCircle, Loader2 } from "lucide-react";
import { apiService, ChatResponse, Citation } from "../services/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatInterfaceProps {
  conversationId: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ conversationId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Chat mutation
  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      apiService.sendChatMessage(conversationId, message),
    onSuccess: (data: ChatResponse) => {
      // Add user message to history
      setMessages((prev) => [...prev, { role: "user", content: input.trim() }]);
      // Add assistant response
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);
      // Update citations (sorted by score, highest first)
      const sortedCitations = [...data.citations].sort(
        (a, b) => b.score - a.score
      );
      setCitations(sortedCitations);
      // Clear input and error
      setInput("");
      setError(null);
    },
    onError: (error: any) => {
      // Extract error message from API response
      const errorMessage =
        error?.message || "Failed to send message. Please try again.";
      setError(errorMessage);
      // Add user message even if API call fails (for UX)
      setMessages((prev) => [...prev, { role: "user", content: input.trim() }]);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedInput = input.trim();
    if (trimmedInput && !chatMutation.isPending) {
      chatMutation.mutate(trimmedInput);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
    // Shift+Enter allows new line (default textarea behavior)
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1);
  };

  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  const isLoading = chatMutation.isPending;
  const isSendDisabled = !input.trim() || isLoading;

  return (
    <div className="flex flex-col md:flex-row h-full gap-4">
      {/* Messages Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto space-y-4 p-4 mb-4">
          {messages.length === 0 ? (
            // Empty state
            <div className="text-center py-12">
              <div className="text-4xl mb-4">💬</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start a conversation
              </h3>
              <p className="text-gray-600">
                Ask a question to get started with your document search
              </p>
            </div>
          ) : (
            // Message history
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">
                    {message.content}
                  </p>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 px-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="text-sm font-medium text-red-900 mb-1">Error</h4>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <div className="flex-1">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                className="form-input resize-none"
                rows={3}
                maxLength={1000}
                disabled={isLoading}
              />
              <div className="text-xs text-gray-500 mt-1 text-right">
                {input.length}/1000
              </div>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={isSendDisabled}
                className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Citations Panel - Responsive: side on desktop, below on mobile */}
      <div className="md:w-80 md:border-l md:border-gray-200 border-t md:border-t-0 bg-gray-50 flex flex-col">
        {citations.length > 0 ? (
          <>
            <div className="p-4 border-b border-gray-200">
              <h4 className="text-sm font-medium text-gray-900">
                Citations ({citations.length})
              </h4>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {citations.map((citation, index) => (
                <div
                  key={`${citation.doc_id}-${citation.chunk_id}`}
                  className="bg-white rounded-lg p-3 border border-gray-200"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-500">
                      #{index + 1}
                    </span>
                    <span className="text-xs font-medium text-blue-600">
                      Score: {formatScore(citation.score)}%
                    </span>
                  </div>
                  <div className="mb-2">
                    <p className="text-xs text-gray-600 mb-1">
                      <span className="font-medium">Doc:</span>{" "}
                      {citation.doc_id}
                    </p>
                    <p className="text-xs text-gray-600 mb-1">
                      <span className="font-medium">Chunk:</span>{" "}
                      {citation.chunk_id}
                    </p>
                    {citation.page_from && citation.page_to && (
                      <p className="text-xs text-gray-600">
                        <span className="font-medium">Pages:</span>{" "}
                        {citation.page_from}-{citation.page_to}
                      </p>
                    )}
                  </div>
                  <p className="text-xs text-gray-800 leading-relaxed">
                    {truncateText(citation.text, 200)}
                  </p>
                </div>
              ))}
            </div>
          </>
        ) : messages.length > 0 ? (
          <div className="p-4">
            <p className="text-sm text-gray-500 text-center">
              No citations available
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default ChatInterface;
