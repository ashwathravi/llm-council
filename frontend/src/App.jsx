import { useState, useEffect, useCallback, lazy, Suspense, useMemo } from 'react';
// import Sidebar from './components/Sidebar';
import CouncilSidebar from './components/CouncilSidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/toaster";
import { useToast } from "@/components/ui/use-toast";
import { Moon, Sun, Menu, LogOut } from "lucide-react";

const Login = lazy(() => import('./components/Login'));
import { useAuth } from './contexts/AuthContextDefinition';
// import './App.css'; // Deprecated

function App() {
  const { user, isLoading: authLoading, logout } = useAuth();
  const { toast } = useToast();
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);

  const [isLoading, setIsLoading] = useState(false);
  // Theme State
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  }, []);

  const mobileBreakpoint = 768; // Tailwind md
  const [isMobile, setIsMobile] = useState(window.innerWidth < mobileBreakpoint);
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth >= mobileBreakpoint);

  // ... (Keep existing loadConversations, loadConversation logic) ...
  const loadConversations = useCallback(async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        logout();
      }
    }
  }, [logout]);

  const loadConversation = useCallback(async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }, []);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < mobileBreakpoint;
      setIsMobile(mobile);
      if (!mobile) {
        setIsSidebarOpen(true);
      } else {
        setIsSidebarOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (user) {
      loadConversations().then(() => {
        const params = new URLSearchParams(window.location.search);
        const convId = params.get('c');
        if (convId) {
          setCurrentConversationId(convId);
        }
      });
    } else {
      setConversations([]);
      setCurrentConversationId(null);
      setCurrentConversation(null);
    }
  }, [loadConversations, user]);

  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const convId = params.get('c');
      if (convId) {
        setCurrentConversationId(convId);
      } else {
        setCurrentConversationId(null);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (currentConversationId && user) {
      loadConversation(currentConversationId);
    } else {
      setCurrentConversation(null);
    }
  }, [currentConversationId, loadConversation, user]);

  const handleNewConversation = useCallback(async (framework, councilModels, chairmanModel) => {
    setIsLoading(true);
    try {
      const data = await api.createConversation(framework, councilModels, chairmanModel);
      setConversations(prev => [data, ...prev]);
      setCurrentConversationId(data.id);
      setCurrentConversation(data);
      const newUrl = `?c=${data.id}`;
      window.history.pushState({ path: newUrl }, '', newUrl);
      return data;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSelectConversation = useCallback((id) => {
    setCurrentConversationId(id);
    const newUrl = id ? `?c=${id}` : window.location.pathname;
    window.history.pushState({ path: newUrl }, '', newUrl);
    if (isMobile) {
      setIsSidebarOpen(false);
    }
  }, [isMobile]);

  const handleSidebarClose = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  // Optimize Sidebar re-renders by extracting only necessary metadata
  // We extract properties first so they can be stable dependencies for useMemo
  const conversationId = currentConversation?.id;
  const conversationTitle = currentConversation?.title;
  const conversationFramework = currentConversation?.framework;
  const conversationCouncilModels = currentConversation?.council_models;
  const conversationChairmanModel = currentConversation?.chairman_model;

  const activeConversationMetadata = useMemo(() => {
    if (!conversationId) return null;
    return {
      id: conversationId,
      title: conversationTitle,
      framework: conversationFramework,
      council_models: conversationCouncilModels,
      chairman_model: conversationChairmanModel,
    };
  }, [
    conversationId,
    conversationTitle,
    conversationFramework,
    conversationCouncilModels,
    conversationChairmanModel
  ]);

  // ... (Keep handleSendMessage logic exactly as is, it's complex) ...
  const handleSendMessage = useCallback(async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        errors: [],
        loading: { stage1: false, stage2: false, stage3: false },
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        // ... (Keep existing switch case logic) ...
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.loading = { ...lastMsg.loading, stage1: true };
              lastMsg.stage1 = [];
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage1_update':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              const currentStage1 = Array.isArray(lastMsg.stage1) ? lastMsg.stage1 : [];
              lastMsg.stage1 = [...currentStage1, event.data];
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage1_error':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              const currentErrors = Array.isArray(lastMsg.errors) ? lastMsg.errors : [];
              lastMsg.errors = [...currentErrors, event.data];
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.stage1 = event.data;
              lastMsg.metadata = {
                ...(lastMsg.metadata || {}),
                ...(event.metadata || {}),
              };
              lastMsg.loading = { ...lastMsg.loading, stage1: false };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.loading = { ...lastMsg.loading, stage2: true };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.stage2 = event.data;
              lastMsg.metadata = {
                ...(lastMsg.metadata || {}),
                ...(event.metadata || {}),
              };
              lastMsg.loading = { ...lastMsg.loading, stage2: false };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.loading = { ...lastMsg.loading, stage3: true };
              lastMsg.stage3 = { model: 'chairman', response: '' };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage3_token':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              if (lastMsg.stage3 && lastMsg.stage3.response !== undefined) {
                lastMsg.stage3 = {
                  ...lastMsg.stage3,
                  response: lastMsg.stage3.response + event.data
                };
              } else {
                lastMsg.stage3 = { model: 'chairman', response: event.data };
              }
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.stage3 = event.data;
              lastMsg.loading = { ...lastMsg.loading, stage3: false };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          case 'title_complete':
            // ⚡ Bolt: Optimize by updating local state instead of re-fetching entire list
            if (event.data?.title) {
              const newTitle = event.data.title;
              setConversations((prev) =>
                prev.map((c) =>
                  c.id === currentConversationId ? { ...c, title: newTitle } : c
                )
              );
              // Only update current conversation if it matches the one that generated the title
              setCurrentConversation((prev) =>
                (prev && prev.id === currentConversationId)
                  ? { ...prev, title: newTitle }
                  : prev
              );
            }
            break;
          case 'complete':
            // ⚡ Bolt: Removed redundant loadConversations() - list order/metadata doesn't change on completion
            setIsLoading(false);
            break;
          case 'error':
            console.error('Stream error:', event.error);
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              const currentErrors = Array.isArray(lastMsg.errors) ? lastMsg.errors : [];
              lastMsg.errors = [...currentErrors, {
                model: 'system',
                error: event.error || 'Unknown error',
              }];
              lastMsg.loading = { stage1: false, stage2: false, stage3: false };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            setIsLoading(false);
            break;
          case 'stage2_skipped':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.stage2 = [];
              lastMsg.metadata = {
                ...(lastMsg.metadata || {}),
                ...(event.metadata || {}),
              };
              lastMsg.loading = { ...lastMsg.loading, stage2: false };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;
          default:
            break;
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  }, [currentConversationId]);

  const handleRetryFailedModels = useCallback(async (messageIndex, models = [], options = {}) => {
    if (!currentConversationId) return null;
    const refreshSynthesis = Boolean(options?.refreshSynthesis);

    try {
      const retryData = await api.retryFailedModels(
        currentConversationId,
        messageIndex,
        models,
        { refreshSynthesis }
      );

      setCurrentConversation((prev) => {
        if (!prev || !Array.isArray(prev.messages)) return prev;
        if (messageIndex < 0 || messageIndex >= prev.messages.length) return prev;

        const messages = [...prev.messages];
        const targetMessage = { ...messages[messageIndex] };
        const existingMetadata = targetMessage.metadata || {};
        const incomingMetadata = retryData?.metadata || {};

        targetMessage.stage1 = Array.isArray(retryData?.stage1)
          ? retryData.stage1
          : targetMessage.stage1;
        targetMessage.stage2 = Array.isArray(retryData?.stage2)
          ? retryData.stage2
          : targetMessage.stage2;
        targetMessage.stage3 = retryData?.stage3 && typeof retryData.stage3 === 'object'
          ? retryData.stage3
          : targetMessage.stage3;
        targetMessage.errors = Array.isArray(retryData?.stage1_errors)
          ? retryData.stage1_errors
          : targetMessage.errors;
        targetMessage.metadata = {
          ...existingMetadata,
          ...incomingMetadata,
          stage1_errors: Array.isArray(retryData?.stage1_errors)
            ? retryData.stage1_errors
            : existingMetadata.stage1_errors,
        };

        messages[messageIndex] = targetMessage;
        return { ...prev, messages };
      });

      const retriedModels = Array.isArray(retryData?.retried_models) ? retryData.retried_models : [];
      const recoveredModels = Array.isArray(retryData?.recovered_models) ? retryData.recovered_models : [];
      const failedModels = Array.isArray(retryData?.failed_models) ? retryData.failed_models : [];

      if (retriedModels.length > 0) {
        if (recoveredModels.length === retriedModels.length && failedModels.length === 0) {
          toast({
            title: "Retry Complete",
            description: `Recovered ${recoveredModels.length} ${recoveredModels.length === 1 ? 'model' : 'models'}.`,
          });
        } else if (recoveredModels.length > 0) {
          toast({
            title: "Retry Partially Complete",
            description: `Recovered ${recoveredModels.length}/${retriedModels.length}; ${failedModels.length} still failing.`,
          });
        } else {
          toast({
            variant: "destructive",
            title: "Retry Unsuccessful",
            description: failedModels.length > 0
              ? `No models recovered. Still failing: ${failedModels.join(', ')}.`
              : "No models recovered.",
          });
        }
      }

      if (refreshSynthesis) {
        if (retryData?.synthesis_refreshed) {
          toast({
            title: "Synthesis Refreshed",
            description: "Stage 2 and Stage 3 were rerun with the latest Stage 1 responses.",
          });
        } else {
          toast({
            variant: "destructive",
            title: "Synthesis Refresh Failed",
            description: retryData?.synthesis_refresh_error || "Could not refresh synthesis.",
          });
        }
      }

      return retryData;
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Failed to retry models';
      toast({
        variant: "destructive",
        title: refreshSynthesis ? "Synthesis Refresh Failed" : "Retry Failed",
        description: detail,
      });
      throw error;
    }
  }, [currentConversationId, toast]);

  if (authLoading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!user) {
    return (
      <Suspense fallback={<div className="flex h-screen items-center justify-center">Loading login...</div>}>
        <Login />
      </Suspense>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {isMobile && isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <CouncilSidebar
        isMobile={isMobile}
        isOpen={isSidebarOpen}
        onClose={handleSidebarClose}
        conversations={conversations}
        activeConversationMetadata={activeConversationMetadata}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />

      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6">
          {isMobile && (
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsSidebarOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
          )}
          <div className="flex-1" />

          <Button variant="ghost" size="icon" onClick={toggleTheme} title="Toggle Theme">
            {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
          </Button>

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium hidden sm:inline-block">{user.name}</span>
            <Button variant="ghost" size="icon" onClick={logout} title="Logout">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-hidden relative">
          <ChatInterface
            key={currentConversationId || 'no-conversation'}
            conversation={currentConversation}
            onSendMessage={handleSendMessage}
            onRetryFailedModels={handleRetryFailedModels}
            isLoading={isLoading}
            isMobile={isMobile}
          />
        </main>
      </div>
      <Toaster />
    </div>
  );
}

export default App;
