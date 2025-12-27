import { useState, useEffect, memo } from 'react';
import './Sidebar.css';
import { api } from '../api';
import ModelSelect from './ModelSelect';

const Sidebar = memo(({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  isMobile,
  isOpen,
  onClose,
}) => {
  const [selectedFramework, setSelectedFramework] = useState('standard');
  const [models, setModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [councilModels, setCouncilModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsError, setModelsError] = useState(null);
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState(null);
  const [showAllHistory, setShowAllHistory] = useState(false);

  // Filter conversations
  const recentConversations = conversations.slice(0, 5);
  const olderConversations = conversations.slice(5);

  useEffect(() => {
    loadModels();
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setStatusError(null);
      const s = await api.getStatus();
      setStatus(s);
    } catch (e) {
      console.error("Failed to load status", e);
      setStatusError("Error");
    }
  };

  const loadModels = async () => {
    setLoadingModels(true);
    try {
      setModelsError(null);
      const data = await api.getModels();
      setModels(data);
      // Set defaults? Or leave empty to use backend defaults
      // Ideally backend defaults should be visible but we don't know them easily without fetching config
      // Let's leave empty and let user know "Default" is used if empty
    } catch (error) {
      console.error("Failed to load models", error);
      setModelsError(error.message || "Failed to load models");
    } finally {
      setLoadingModels(false);
    }
  };

  const handleNewChat = () => {
    // Pass selected models to parent
    console.log("Sidebar: handleNewChat triggered", { selectedFramework, councilModels, chairmanModel });
    onNewConversation(selectedFramework, councilModels, chairmanModel);
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation(); // Prevent selecting the chat
    if (!confirm("Are you sure you want to delete this conversation?")) return;

    try {
      await api.deleteConversation(id);
      // We need to trigger a refresh in the parent. 
      // ideally parent should pass a refresh callback or we reload
      // For now, let's reload the page or assume parent updates?
      // Actually, standard pattern is parent passes 'onDelete' or we reload.
      // Since we don't have 'onDelete' prop yet, let's ask user to refresh or reload window.
      window.location.reload();
    } catch (err) {
      console.error("Failed to delete", err);
      alert("Failed to delete conversation");
    }
  };

  return (
    <div className={`sidebar ${isMobile ? 'mobile' : ''} ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <div className="header-title-row">
          <h2>LLM Council</h2>
          {status && (
            <div className={`status-badge ${status.storage_mode === 'database' ? 'status-db' : 'status-file'}`}
              title={`Origin: ${status.origin}`}>
              {status.storage_mode === 'database' ? 'DB' : 'FILE'}
            </div>
          )}
          {statusError && (
            <div className="status-badge status-file" title="Failed to fetch backend status">
              OFFLINE
            </div>
          )}
          {isMobile && (
            <button
              type="button"
              className="sidebar-close-btn"
              onClick={onClose}
              aria-label="Close navigation"
            >
              ×
            </button>
          )}
        </div>

        <button className="new-conversation-btn" onClick={handleNewChat}>
          <span>+</span> New Conversation
        </button>

        <div className="framework-select-container">
          <div className="label-with-info">
            <label>Council Mode</label>
            <div className="info-icon-wrapper">
              <span className="info-icon">ℹ️</span>
              <div className="mode-tooltip">
                <div className="tooltip-item">
                  <strong>Standard Council</strong>
                  <p>Models answer individually, rank each other, and a Chairman synthesizes the best answer.</p>
                </div>
                <div className="tooltip-item">
                  <strong>Chain of Debate</strong>
                  <p>Models answer, then critique each other's arguments to find logical flaws before synthesis.</p>
                </div>
                <div className="tooltip-item">
                  <strong>Six Thinking Hats</strong>
                  <p>Models are assigned specific cognitive perspectives (Facts, Feelings, Risks, Benefits, Creativity, Process) to ensure holistic coverage.</p>
                </div>
                <div className="tooltip-item">
                  <strong>Ensemble (Fast)</strong>
                  <p>Parallel execution for quick consensus without the peer-review stage.</p>
                </div>
              </div>
            </div>
          </div>
          <select
            value={selectedFramework}
            onChange={(e) => setSelectedFramework(e.target.value)}
            className="framework-select"
          >
            <option value="standard">Standard Council</option>
            <option value="debate">Chain of Debate</option>
            <option value="six_hats">Six Thinking Hats</option>
            <option value="ensemble">Ensemble (Fast)</option>
          </select>
        </div>

        {/* Model Selection */}
        <div className="model-selection-section">
          <ModelSelect
            label="Chairman Model"
            options={models}
            value={chairmanModel}
            onChange={setChairmanModel}
            multi={false}
            disabled={loadingModels || !!modelsError}
          />

          <ModelSelect
            label="Council Models (Max 5)"
            options={models}
            value={councilModels}
            onChange={setCouncilModels}
            multi={true}
            maxSelected={5}
            disabled={loadingModels || !!modelsError}
          />
          {modelsError && (
            <div className="model-error">
              {modelsError}
            </div>
          )}
        </div>
      </div>

      <div className="conversations-list">
        {conversations.length > 0 && <div className="list-section-header">Recent</div>}
        {recentConversations.map((conv) => (
          <div
            key={conv.id}
            className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''
              }`}
            onClick={() => onSelectConversation(conv.id)}
          >
            <div className="conversation-content-wrapper">
              <div className="conversation-title">{conv.title}</div>
              <div className="conversation-meta">
                {new Date(conv.created_at).toLocaleDateString()}
                {conv.framework && ` • ${conv.framework}`}
              </div>
            </div>
            <button
              className="delete-btn"
              onClick={(e) => handleDelete(e, conv.id)}
              title="Delete conversation"
            >
              ×
            </button>
          </div>
        ))}

        {olderConversations.length > 0 && (
          <>
            <button
              className="toggle-history-btn"
              onClick={() => setShowAllHistory(!showAllHistory)}
            >
              {showAllHistory ? "Hide Older Conversations" : `Show ${olderConversations.length} Older Conversations`}
            </button>

            {showAllHistory && (
              <>
                <div className="list-section-header">History</div>
                {olderConversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''
                      }`}
                    onClick={() => onSelectConversation(conv.id)}
                  >
                    <div className="conversation-content-wrapper">
                      <div className="conversation-title">{conv.title}</div>
                      <div className="conversation-meta">
                        {new Date(conv.created_at).toLocaleDateString()}
                        {conv.framework && ` • ${conv.framework}`}
                      </div>
                    </div>
                    <button
                      className="delete-btn"
                      onClick={(e) => handleDelete(e, conv.id)}
                      title="Delete conversation"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </>
            )}
          </>
        )}

        {conversations.length === 0 && (
          <div className="no-conversations">
            No conversations yet. Start a new one!
          </div>
        )}
      </div>
    </div>
  );
});

export default Sidebar;
