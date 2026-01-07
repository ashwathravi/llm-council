import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';

const Login = lazy(() => import('./components/Login'));
import { useAuth } from './contexts/AuthContextDefinition';
import './App.css';

function App() {
  const { user, isLoading: authLoading, logout } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  // Theme State
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  }, []);

  const mobileBreakpoint = 900;
  const [isMobile, setIsMobile] = useState(window.innerWidth < mobileBreakpoint);
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth >= mobileBreakpoint);

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
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load conversations on mount or when user changes
  useEffect(() => {
    if (user) {
      loadConversations().then(() => {
        // Check for URL query param for conversation ID
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

  // Handle browser back/forward buttons
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

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId && user) {
      loadConversation(currentConversationId);
    } else {
      setCurrentConversation(null);
    }
  }, [currentConversationId, loadConversation, user]);

  const handleNewConversation = useCallback(async (framework, councilModels, chairmanModel) => {
    console.log("App: handleNewConversation received", { framework, councilModels, chairmanModel });
    setIsLoading(true);
    try {
      const data = await api.createConversation(framework, councilModels, chairmanModel);
      setConversations(prev => [data, ...prev]);
      setCurrentConversationId(data.id);
      // Store framework/models in local state if needed, or just let backend handle it
      // We might want to pass these to sendMessage if backend needs them, but backend stores them in conversation now.
      // So no need to track standard/custom models here for sending messages.
    } catch (error) {
      console.error('Failed to create conversation:', error);
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

  const handleSendMessage = useCallback(async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        errors: [],
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              lastMsg.loading = { ...lastMsg.loading, stage1: true };
              lastMsg.stage1 = []; // Initialize empty array
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage1_update':
            // Append single model result
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastIndex = messages.length - 1;
              const lastMsg = { ...messages[lastIndex] };
              // Ensure stage1 is an array
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
              // Prefer the complete list from server to ensure order/consistency
              lastMsg.stage1 = event.data;
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
              lastMsg.metadata = event.metadata;
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
              // Initialize with empty response so we can append tokens
              lastMsg.stage3 = { model: 'chairman', response: '' };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;

          case 'stage3_token':
            // Append token to response
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
                // Fallback init
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
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
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
              if (lastMsg.loading) {
                lastMsg.loading = {
                  ...lastMsg.loading,
                  stage1: false,
                  stage2: false,
                  stage3: false,
                };
              }
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
              lastMsg.stage2 = []; // Empty or skipped
              lastMsg.metadata = event.metadata;
              lastMsg.loading = { ...lastMsg.loading, stage2: false };
              messages[lastIndex] = lastMsg;
              return { ...prev, messages };
            });
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  }, [currentConversationId, loadConversations]);

  if (authLoading) return <div className="loading">Loading...</div>;
  if (!user) {
    return (
      <Suspense fallback={<div className="loading">Loading login...</div>}>
        <Login />
      </Suspense>
    );
  }

  return (
    <div className="app">
      {isMobile && isSidebarOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          onClick={() => setIsSidebarOpen(false)}
          aria-label="Close navigation"
        />
      )}
      <Sidebar
        isMobile={isMobile}
        isOpen={isSidebarOpen}
        onClose={handleSidebarClose}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <div className="main-content">
        <div className="user-header">
          <button
            type="button"
            className="menu-btn"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <span aria-hidden="true">☰</span>
          </button>
          <div className="theme-toggle-container">
            <button
              onClick={toggleTheme}
              className="theme-toggle"
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
              title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
          </div>
          <span>{user.name}</span>
          <button onClick={logout} className="logout-btn">Logout</button>
        </div>
        <ChatInterface
          conversation={currentConversation}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

export default App;
