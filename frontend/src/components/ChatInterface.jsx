
import { useEffect, useRef, useState } from 'react';
import MessageItem from './MessageItem';
import ChatHeader from './ChatHeader';
import ChatInput from './ChatInput';
import { BrainCircuit } from "lucide-react";

const STARTER_PROMPTS = [
  'Give me a concise implementation plan for this feature, including risks and rollout steps.',
  'Compare two technical approaches and recommend one with trade-offs.',
  'Review this idea for accessibility and performance gaps before we ship.',
];

export default function ChatInterface({
  conversation,
  onSendMessage,
  onRetryFailedModels,
  isLoading,
}) {
  const messagesEndRef = useRef(null);
  const [prefilledPrompt, setPrefilledPrompt] = useState('');

  useEffect(() => {
    if (!conversation || conversation.messages.length > 0) return undefined;

    const onStarterPromptShortcut = (event) => {
      if (!event.altKey) return;

      const index = Number(event.key) - 1;
      if (Number.isNaN(index) || index < 0 || index >= STARTER_PROMPTS.length) return;

      event.preventDefault();
      setPrefilledPrompt(STARTER_PROMPTS[index]);
    };

    window.addEventListener('keydown', onStarterPromptShortcut);
    return () => window.removeEventListener('keydown', onStarterPromptShortcut);
  }, [conversation]);

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
            <div className="mt-3 rounded-md border border-dashed px-3 py-2 text-xs">
              <p>Shortcuts: <span className="font-medium">Alt+1/2/3</span> for starter prompts · <span className="font-medium">Ctrl/Cmd+Enter</span> to send</p>
            </div>
            <div className="mt-5 max-w-2xl">
              <p className="text-xs uppercase tracking-wide mb-2">Starter prompts</p>
              <div className="flex flex-wrap justify-center gap-2">
                {STARTER_PROMPTS.map((prompt, index) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setPrefilledPrompt(prompt)}
                    className="rounded-full border bg-background px-3 py-1.5 text-xs text-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label={`Use starter prompt ${index + 1}: ${prompt}`}
                  >
                    {index + 1}. {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <MessageItem
              key={index}
              msg={msg}
              messageIndex={index}
              onRetryFailedModels={onRetryFailedModels}
            />
          ))
        )}


        <div ref={messagesEndRef} className="h-1" />
      </div>

      <ChatInput
        conversationId={conversation.id}
        isLoading={isLoading}
        onSendMessage={onSendMessage}
        prefilledPrompt={prefilledPrompt}
      />
    </div>
  );
}
