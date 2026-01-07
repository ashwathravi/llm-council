import React, { memo, useState, useEffect } from 'react';
import { api } from '../api';
import './ChatInterface.css';

const ChatHeader = memo(({ title, framework, conversationId }) => {
  const [copySuccess, setCopySuccess] = useState(false);

  useEffect(() => {
    let timeout;
    if (copySuccess) {
      timeout = setTimeout(() => {
        setCopySuccess(false);
      }, 2000);
    }
    return () => clearTimeout(timeout);
  }, [copySuccess]);

  const handleExport = async (format) => {
    if (!conversationId) return;
    try {
      await api.exportConversation(conversationId, format);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export conversation');
    }
  };

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      setCopySuccess(true);
    }).catch(err => {
      console.error('Failed to copy link:', err);
    });
  };

  return (
    <div className="chat-header">
      <div className="header-info">
        <h3>{title || 'New Conversation'}</h3>
        <span className="model-info">{framework}</span>
      </div>
      <div className="header-actions">
        <button
          className="export-btn icon-btn"
          onClick={() => handleExport('md')}
          title="Export to Markdown"
          aria-label="Export conversation to Markdown"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <path d="M12 18v-6"></path>
            <path d="M9 15l3 3 3-3"></path>
          </svg>
        </button>
        <button
          className="export-btn icon-btn"
          onClick={() => handleExport('pdf')}
          title="Export to PDF"
          aria-label="Export conversation to PDF"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <path d="M16 13H8"></path>
            <path d="M16 17H8"></path>
            <path d="M10 9H8"></path>
          </svg>
        </button>
        <button
          className={`export-btn icon-btn ${copySuccess ? 'success' : ''}`}
          onClick={handleCopyLink}
          title={copySuccess ? "Copied!" : "Copy Link to Chat"}
          aria-label={copySuccess ? "Link copied to clipboard" : "Copy link to chat"}
        >
          {copySuccess ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="green" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
          )}
        </button>
      </div>
    </div>
  );
});

export default ChatHeader;
