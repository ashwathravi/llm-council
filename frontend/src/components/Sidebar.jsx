import { useState, useEffect } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}) {
  const [selectedFramework, setSelectedFramework] = useState('standard');

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>

        <div className="framework-select-container">
          <label htmlFor="framework-select">Council Mode:</label>
          <select
            id="framework-select"
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

        <button className="new-conversation-btn" onClick={() => onNewConversation(selectedFramework)}>
          + New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''
                }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Conversation'}
              </div>
              <div className="conversation-meta">
                {conv.message_count} messages
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
