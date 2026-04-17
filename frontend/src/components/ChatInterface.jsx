
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MessageItem from './MessageItem';
import ChatHeader from './ChatHeader';
import ChatInput from './ChatInput';
import ConversationNavigator from './ConversationNavigator';
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { BrainCircuit, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { buildConversationOutline, buildTurnAnchorId } from "@/lib/conversationNavigator";

const NEAR_BOTTOM_THRESHOLD_PX = 120;

export default function ChatInterface({
  conversation,
  onSendMessage,
  onRetryFailedModels,
  isLoading,
  isMobile = false,
  isNavigatorOpen = false,
  onNavigatorOpenChange,
}) {
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const highlightTimeoutRef = useRef(null);
  const [activeAnchorId, setActiveAnchorId] = useState(null);
  const [highlightedAnchorId, setHighlightedAnchorId] = useState(null);
  const [shouldAutoFollow, setShouldAutoFollow] = useState(true);
  const [isNearBottom, setIsNearBottom] = useState(true);

  const outlineItems = useMemo(
    () => buildConversationOutline(conversation?.messages || [], isLoading),
    [conversation?.messages, isLoading]
  );
  const resolvedActiveAnchorId = useMemo(() => {
    if (!outlineItems.length) return null;
    if (activeAnchorId && outlineItems.some((item) => item.anchorId === activeAnchorId)) {
      return activeAnchorId;
    }
    return outlineItems[outlineItems.length - 1].anchorId;
  }, [activeAnchorId, outlineItems]);

  const scrollToBottom = useCallback((behavior = 'auto') => {
    const container = messagesContainerRef.current;
    if (!container) return;
    container.scrollTo({
      top: container.scrollHeight,
      behavior,
    });
  }, []);

  const isNearBottomInViewport = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distanceFromBottom <= NEAR_BOTTOM_THRESHOLD_PX;
  }, []);

  const highlightAnchor = useCallback((anchorId) => {
    if (highlightTimeoutRef.current) {
      window.clearTimeout(highlightTimeoutRef.current);
    }
    setHighlightedAnchorId(anchorId);
    highlightTimeoutRef.current = window.setTimeout(() => {
      setHighlightedAnchorId((current) => (current === anchorId ? null : current));
    }, 1800);
  }, []);

  const setNavigatorOpen = useCallback((nextOpen) => {
    if (typeof onNavigatorOpenChange === 'function') {
      onNavigatorOpenChange(Boolean(nextOpen));
    }
  }, [onNavigatorOpenChange]);

  const handleJumpToLatest = useCallback(() => {
    const latestAnchorId = outlineItems[outlineItems.length - 1]?.anchorId || null;
    if (latestAnchorId) {
      setActiveAnchorId(latestAnchorId);
      highlightAnchor(latestAnchorId);
    }
    setShouldAutoFollow(true);
    setIsNearBottom(true);
    scrollToBottom('smooth');
    if (isMobile) {
      setNavigatorOpen(false);
    }
  }, [highlightAnchor, isMobile, outlineItems, scrollToBottom, setNavigatorOpen]);

  const handleJumpToTop = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const firstAnchorId = outlineItems[0]?.anchorId || null;
    if (firstAnchorId) {
      setActiveAnchorId(firstAnchorId);
      highlightAnchor(firstAnchorId);
    }
    setShouldAutoFollow(false);
    setIsNearBottom(false);
    container.scrollTo({ top: 0, behavior: 'smooth' });
    if (isMobile) {
      setNavigatorOpen(false);
    }
  }, [highlightAnchor, isMobile, outlineItems, setNavigatorOpen]);

  const handleJumpToAnchor = useCallback((anchorId) => {
    if (!anchorId) return;
    const target = document.getElementById(anchorId);
    if (!target) return;

    setShouldAutoFollow(false);
    setIsNearBottom(false);
    setActiveAnchorId(anchorId);
    highlightAnchor(anchorId);
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (isMobile) {
      setNavigatorOpen(false);
    }
  }, [highlightAnchor, isMobile, setNavigatorOpen]);

  const handleJumpToFirst = useCallback(() => {
    const firstAnchorId = outlineItems[0]?.anchorId;
    if (!firstAnchorId) return;
    if (outlineItems.length <= 1) {
      handleJumpToTop();
      return;
    }
    handleJumpToAnchor(firstAnchorId);
  }, [handleJumpToAnchor, handleJumpToTop, outlineItems]);

  const handleMessagesScroll = useCallback(() => {
    const nearBottom = isNearBottomInViewport();
    setIsNearBottom(nearBottom);
    setShouldAutoFollow((current) => {
      if (nearBottom) return true;
      if (current) return false;
      return current;
    });
  }, [isNearBottomInViewport]);

  useEffect(() => {
    if (!conversation) return;
    if (!shouldAutoFollow) return;
    scrollToBottom(isLoading ? 'auto' : 'smooth');
  }, [conversation, conversation?.messages, isLoading, scrollToBottom, shouldAutoFollow]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container || !outlineItems.length) return undefined;

    const anchors = outlineItems
      .map((item) => document.getElementById(item.anchorId))
      .filter(Boolean);

    if (anchors.length === 0) return undefined;

    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      const updateActiveAnchor = () => {
        const containerTop = container.getBoundingClientRect().top + 24;
        let bestAnchor = anchors[0];
        let bestDistance = Number.POSITIVE_INFINITY;

        anchors.forEach((anchor) => {
          const distance = Math.abs(anchor.getBoundingClientRect().top - containerTop);
          if (distance < bestDistance) {
            bestDistance = distance;
            bestAnchor = anchor;
          }
        });

        if (bestAnchor?.id) {
          setActiveAnchorId(bestAnchor.id);
        }
      };

      updateActiveAnchor();
      container.addEventListener('scroll', updateActiveAnchor, { passive: true });
      return () => {
        container.removeEventListener('scroll', updateActiveAnchor);
      };
    }

    const ratioById = new Map();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          ratioById.set(entry.target.id, entry.isIntersecting ? entry.intersectionRatio : 0);
        });

        let bestAnchorId = null;
        let bestRatio = 0;
        ratioById.forEach((ratio, anchorId) => {
          if (ratio > bestRatio) {
            bestRatio = ratio;
            bestAnchorId = anchorId;
          }
        });

        if (bestAnchorId) {
          setActiveAnchorId(bestAnchorId);
        }
      },
      {
        root: container,
        rootMargin: '-10% 0px -70% 0px',
        threshold: [0, 0.2, 0.4, 0.6, 0.8, 1],
      }
    );

    anchors.forEach((anchor) => observer.observe(anchor));

    return () => {
      observer.disconnect();
    };
  }, [conversation?.id, outlineItems]);

  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) {
        window.clearTimeout(highlightTimeoutRef.current);
      }
    };
  }, []);

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
    <div className="flex h-full bg-background">
      <div className="flex min-w-0 flex-1 flex-col bg-background relative">
        <ChatHeader
          title={conversation.title}
          conversationId={conversation.id}
          framework={conversation.framework}
          councilModels={conversation.council_models}
          chairmanModel={conversation.chairman_model}
          navigatorItemCount={outlineItems.length}
        />

        <div className="relative flex-1 min-h-0">
          {/* Messages Area - Using overflow-y-auto for better controlled smart-follow behavior */}
          <div
            ref={messagesContainerRef}
            onScroll={handleMessagesScroll}
            className="h-full overflow-y-auto p-4 md:p-6 space-y-6"
          >
            {conversation.messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground opacity-70">
                <h2 className="text-xl font-semibold mb-2">Start a conversation</h2>
                <p>Ask a question to consult the LLM Council</p>
              </div>
            ) : (
              conversation.messages.map((msg, index) => {
                const isUserTurn = msg?.role === 'user';
                const anchorId = isUserTurn ? buildTurnAnchorId(index) : null;
                const isActiveTurn = Boolean(anchorId && anchorId === resolvedActiveAnchorId);
                const isHighlightedTurn = Boolean(anchorId && anchorId === highlightedAnchorId);

                return (
                  <div
                    key={index}
                    id={anchorId || undefined}
                    data-turn-anchor={isUserTurn ? 'true' : undefined}
                    className={cn(
                      isUserTurn && 'scroll-mt-24 rounded-md transition-colors',
                      isActiveTurn && 'ring-1 ring-primary/30',
                      isHighlightedTurn && 'bg-primary/10'
                    )}
                  >
                    <MessageItem
                      msg={msg}
                      messageIndex={index}
                      onRetryFailedModels={onRetryFailedModels}
                    />
                  </div>
                );
              })
            )}

            <div ref={messagesEndRef} className="h-1" />
          </div>

          {!isNearBottom && conversation.messages.length > 0 && (
            <Button
              type="button"
              size="sm"
              className="absolute bottom-4 right-4 z-20 shadow-lg"
              onClick={handleJumpToLatest}
              aria-label="Jump to latest message"
            >
              <ArrowDown className="mr-1 h-4 w-4" />
              Jump to latest
            </Button>
          )}
        </div>

        <ChatInput
          conversationId={conversation.id}
          isLoading={isLoading}
          onSendMessage={onSendMessage}
        />
      </div>

      {!isMobile && isNavigatorOpen && (
        <aside className="hidden md:flex h-full w-[320px] max-w-[35vw] shrink-0 border-l bg-background/95">
          <ConversationNavigator
            items={outlineItems}
            activeAnchorId={resolvedActiveAnchorId}
            onJumpToTop={handleJumpToTop}
            onJumpToAnchor={handleJumpToAnchor}
            onJumpToFirst={handleJumpToFirst}
            onJumpToLatest={handleJumpToLatest}
            onClose={() => setNavigatorOpen(false)}
          />
        </aside>
      )}

      {isMobile && (
        <Dialog open={isNavigatorOpen} onOpenChange={setNavigatorOpen}>
          <DialogContent className="left-0 right-0 top-auto bottom-0 h-[78vh] max-w-none translate-x-0 translate-y-0 rounded-b-none rounded-t-xl p-0 data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom">
            <DialogTitle className="sr-only">Conversation Navigator</DialogTitle>
            <DialogDescription className="sr-only">
              Jump to different user turns in the conversation.
            </DialogDescription>
            <ConversationNavigator
              items={outlineItems}
              activeAnchorId={resolvedActiveAnchorId}
              onJumpToTop={handleJumpToTop}
              onJumpToAnchor={handleJumpToAnchor}
              onJumpToFirst={handleJumpToFirst}
              onJumpToLatest={handleJumpToLatest}
              onClose={() => setNavigatorOpen(false)}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
