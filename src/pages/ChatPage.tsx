import React, { useState } from "react";
import ChatInterface from "../components/ChatInterface";

const ChatPage: React.FC = () => {
  // Generate stable conversation_id on component mount (UUID)
  const [conversationId] = useState(() => {
    // Use crypto.randomUUID() if available, otherwise fallback
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    // Fallback for older browsers
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  });

  return (
    <div className="max-w-6xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Chat</h1>
        <p className="text-gray-600">
          Ask questions in natural language and receive answers with citations
          from your document corpus
        </p>
      </div>

      <div className="card">
        <div className="h-[600px] flex flex-col">
          <ChatInterface conversationId={conversationId} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
