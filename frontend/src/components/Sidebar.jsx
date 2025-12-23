import { useState, useEffect } from 'react';
import './Sidebar.css';
import { api } from '../api';
import ModelSelect from './ModelSelect';

const Sidebar = ({ conversations, currentConversationId, onSelectConversation, onNewConversation }) => {
  const [selectedFramework, setSelectedFramework] = useState('standard');
  const [models, setModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [councilModels, setCouncilModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState(null);

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
      const data = await api.getModels();
      setModels(data);
      // Set defaults? Or leave empty to use backend defaults
      // Ideally backend defaults should be visible but we don't know them easily without fetching config
      // Let's leave empty and let user know "Default" is used if empty
    } catch (error) {
      console.error("Failed to load models", error);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleNewChat = () => {
    // Pass selected models to parent
    onNewConversation(selectedFramework, councilModels, chairmanModel);
  };

  return (
    <div className="sidebar">
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
        </div>

        <div className="framework-select-container">
          <label>Council Mode</label>
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
          />

          <ModelSelect
            label="Council Models (Max 5)"
            options={models}
            value={councilModels}
            onChange={setCouncilModels}
            multi={true}
            maxSelected={5}
          />
        </div>

        <button className="new-chat-btn" onClick={handleNewChat}>
          + New Conversation
        </button>
      </div>

      <div className="conversations-list">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''
              }`}
            onClick={() => onSelectConversation(conv.id)}
          >
            <div className="conversation-title">{conv.title}</div>
            <div className="conversation-meta">
              {new Date(conv.created_at).toLocaleDateString()}
              {conv.framework && ` • ${conv.framework}`}
            </div>
          </div>
        ))}

        {conversations.length === 0 && (
          <div className="no-conversations">
            No conversations yet. Start a new one!
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
