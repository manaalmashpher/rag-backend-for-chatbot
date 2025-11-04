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
    <div className="flex flex-col bg-white">
      <ChatInterface conversationId={conversationId} />
    </div>
  );
};

export default ChatPage;
