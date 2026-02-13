
import { useEffect, useRef } from 'react';
import MessageItem from './MessageItem';
import ChatHeader from './ChatHeader';
import ChatInput from './ChatInput';
import { BrainCircuit } from "lucide-react";

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages, isLoading]);

  if (!conversation) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-muted-foreground animate-in fade-in zoom-in-95 duration-300">
        <div className="bg-muted/50 p-6 rounded-full mb-6">
          <BrainCircuit className="h-16 w-16 opacity-50" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Welcome to LLM Council</h2>
        <p className="max-w-md">Create a new conversation from the sidebar to begin consulting with multiple AI models simultaneously.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background relative">
      <ChatHeader
        title={conversation.title}
        conversationId={conversation.id}
        framework={conversation.framework}
        councilModels={conversation.council_models}
        chairmanModel={conversation.chairman_model}
      />

      {/* Messages Area - Using overflow-y-auto for better scroll-to-bottom behavior vs ScrollArea */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {conversation.messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground opacity-70">
            <h2 className="text-xl font-semibold mb-2">Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <MessageItem key={index} msg={msg} />
          ))
        )}


        <div ref={messagesEndRef} className="h-1" />
      </div>

      <ChatInput
        conversationId={conversation.id}
        isLoading={isLoading}
        onSendMessage={onSendMessage}
      />
    </div>
  );
}
