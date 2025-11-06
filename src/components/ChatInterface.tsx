import React, { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Send,
  AlertCircle,
  Loader2,
  User,
  Bot,
  FileText,
  ExternalLink,
} from "lucide-react";
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
    <div className="flex flex-col md:flex-row w-full gap-0">
      {/* Messages Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        <div className="space-y-6 p-4 md:p-6">
          {messages.length === 0 ? (
            // Enhanced Empty state
            <div
              className="flex flex-col items-center justify-center py-12"
              style={{ minHeight: "400px" }}
            >
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-6 shadow-lg">
                <Bot className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Start a conversation
              </h3>
              <p className="text-gray-600 text-center max-w-md">
                Ask questions in natural language and receive answers with
                citations from your document corpus
              </p>
              <div className="mt-8 flex flex-wrap gap-2 justify-center">
                <span className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm">
                  Try: "What neural networks are used?"
                </span>
                <span className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm">
                  Or: "Explain the architecture"
                </span>
              </div>
            </div>
          ) : (
            // Enhanced Message history
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex items-start gap-3 ${
                  message.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === "user" ? "bg-blue-600" : "bg-gray-200"
                  }`}
                >
                  {message.role === "user" ? (
                    <User className="h-4 w-4 text-white" />
                  ) : (
                    <Bot className="h-4 w-4 text-gray-700" />
                  )}
                </div>
                {/* Message bubble */}
                <div
                  className={`flex-1 max-w-[80%] ${
                    message.role === "user"
                      ? "flex justify-end"
                      : "flex justify-end"
                  }`}
                >
                  <div
                    className={`rounded-2xl px-4 py-3 shadow-sm ${
                      message.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-md"
                        : "bg-gray-50 text-gray-900 border border-gray-200 rounded-tl-md mr-auto"
                    }`}
                  >
                    <p className="text-base leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                <Bot className="h-4 w-4 text-gray-700" />
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span className="text-sm text-gray-600">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-4 md:px-6 pb-4">
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3 shadow-sm">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-red-900 mb-1">
                  Error
                </h4>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* ChatGPT-style Input Form */}
        <form
          onSubmit={handleSubmit}
          style={{
            position: "sticky",
            bottom: "0.5rem",
            zIndex: 10,
            backgroundColor: "#ffffff",
            paddingTop: "2rem",
            paddingBottom: "2rem",
            marginTop: "auto",
          }}
        >
          <div
            style={{
              width: "100%",
              paddingLeft: "1rem",
              paddingRight: "1rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "center" }}>
              <div
                style={{
                  position: "relative",
                  width: "90%",
                  maxWidth: "900px",
                  minWidth: "400px",
                }}
              >
                <div
                  style={{
                    position: "relative",
                    display: "flex",
                    alignItems: "flex-end",
                    borderRadius: "9999px",
                    border: "1px solid #d1d5db",
                    backgroundColor: "#ffffff",
                    boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
                    overflow: "hidden",
                  }}
                >
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Message..."
                    rows={1}
                    style={{
                      width: "100%",
                      minHeight: "52px",
                      maxHeight: "200px",
                      borderRadius: "9999px",
                      paddingLeft: "20px",
                      paddingRight: "56px",
                      paddingTop: "14px",
                      paddingBottom: "14px",
                      lineHeight: "1.5",
                      resize: "none",
                      outline: "none",
                      fontSize: "1rem",
                      border: "none",
                      backgroundColor: "transparent",
                      overflowY: "auto",
                      scrollbarWidth: "thin",
                      scrollbarColor: "#cbd5e1 transparent",
                    }}
                    onFocus={(e) => {
                      const wrapper = e.target.parentElement as HTMLElement;
                      if (wrapper) {
                        wrapper.style.borderColor = "#9ca3af";
                        wrapper.style.boxShadow =
                          "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)";
                      }
                    }}
                    onBlur={(e) => {
                      const wrapper = e.target.parentElement as HTMLElement;
                      if (wrapper) {
                        wrapper.style.borderColor = "#d1d5db";
                        wrapper.style.boxShadow =
                          "0 1px 2px 0 rgb(0 0 0 / 0.05)";
                      }
                    }}
                    onMouseEnter={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      const wrapper = target.parentElement as HTMLElement;
                      if (wrapper && document.activeElement !== target) {
                        wrapper.style.boxShadow =
                          "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      const wrapper = target.parentElement as HTMLElement;
                      if (wrapper && document.activeElement !== target) {
                        wrapper.style.boxShadow =
                          "0 1px 2px 0 rgb(0 0 0 / 0.05)";
                      }
                    }}
                    maxLength={1000}
                    disabled={isLoading}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      const wrapper = target.parentElement as HTMLElement;
                      target.style.height = "auto";
                      const newHeight = Math.min(target.scrollHeight, 200);
                      target.style.height = `${newHeight}px`;
                      // Adjust border radius based on height - more pill-like when short
                      if (newHeight <= 60) {
                        target.style.borderRadius = "9999px";
                        if (wrapper) wrapper.style.borderRadius = "9999px";
                      } else {
                        target.style.borderRadius = "24px";
                        if (wrapper) wrapper.style.borderRadius = "24px";
                      }
                    }}
                  />
                  <button
                    type="submit"
                    disabled={isSendDisabled}
                    style={{
                      position: "absolute",
                      right: "8px",
                      bottom: "8px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "9999px",
                      backgroundColor: "#2563eb",
                      color: "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: "none",
                      cursor: isSendDisabled ? "not-allowed" : "pointer",
                      opacity: isSendDisabled ? 0.5 : 1,
                      transition: "background-color 0.15s ease-in-out",
                      outline: "none",
                    }}
                    onMouseEnter={(e) => {
                      if (!isSendDisabled) {
                        e.currentTarget.style.backgroundColor = "#1d4ed8";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSendDisabled) {
                        e.currentTarget.style.backgroundColor = "#2563eb";
                      }
                    }}
                    aria-label="Send message"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <div className="flex items-center justify-between mt-2 px-2">
                  <span className="text-xs text-gray-400">
                    {input.length}/1000
                  </span>
                  <span className="text-xs text-gray-400">
                    Press Enter to send
                  </span>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* Enhanced Citations Panel - Responsive: side on desktop, below on mobile */}
      <div
        className="md:w-80 border-t md:border-t-0 bg-gray-100 flex flex-col"
        style={{
          position: "sticky",
          top: "4rem",
          height: "calc(100vh - 4rem)",
          alignSelf: "flex-start",
          overflowY: "auto",
          borderRadius: "0.75rem",
        }}
      >
        {citations.length > 0 ? (
          <>
            <div className="p-4 md:p-5 border-b border-gray-200 bg-gray-100">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-gray-600" />
                <h4 className="text-sm font-semibold text-gray-900">
                  Citations
                </h4>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                  {citations.length}
                </span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 md:p-5 space-y-3">
              {citations.map((citation, index) => (
                <div
                  key={`${citation.doc_id}-${citation.chunk_id}`}
                  className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                        {index + 1}
                      </span>
                      <span className="text-xs font-medium text-gray-600">
                        #{citation.doc_id}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-1 bg-green-50 rounded-full">
                      <span className="text-xs font-semibold text-green-700">
                        {formatScore(citation.score)}%
                      </span>
                    </div>
                  </div>
                  <div className="space-y-1.5 mb-3 pb-3 border-b border-gray-100">
                    <div className="flex items-center gap-2 text-xs text-gray-600">
                      <span className="font-medium">Chunk:</span>
                      <span>{citation.chunk_id}</span>
                    </div>
                    {citation.page_from && citation.page_to && (
                      <div className="flex items-center gap-2 text-xs text-gray-600">
                        <span className="font-medium">Pages:</span>
                        <span>
                          {citation.page_from}-{citation.page_to}
                        </span>
                      </div>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed line-clamp-3">
                    {truncateText(citation.text, 200)}
                  </p>
                  <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-end">
                    <span className="text-xs text-blue-600 font-medium group-hover:text-blue-700 flex items-center gap-1">
                      View source
                      <ExternalLink className="h-3 w-3" />
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center p-8 h-full">
            <FileText className="h-12 w-12 text-gray-300 mb-3" />
            <p className="text-sm text-gray-500 text-center">
              No citations available
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;
