import { useState, useEffect, useRef } from 'react';
import MessageItem from './MessageItem';
import './ChatInterface.css';
import { api } from '../api';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [copySuccess, setCopySuccess] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  useEffect(() => {
    setUploadError('');
    setUploading(false);
    setUploadProgress(0);
    if (!conversation?.id) {
      setDocuments([]);
      setDocumentsLoading(false);
      return;
    }

    const loadDocuments = async () => {
      setDocumentsLoading(true);
      try {
        const docs = await api.listDocuments(conversation.id);
        setDocuments(docs);
      } catch (error) {
        console.error('Failed to load documents:', error);
      } finally {
        setDocumentsLoading(false);
      }
    };

    loadDocuments();
  }, [conversation?.id]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleExport = async (format) => {
    try {
      await import('../api').then(m => m.api.exportConversation(conversation.id, format));
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

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const formatBytes = (bytes) => {
    if (!bytes && bytes !== 0) return '';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), sizes.length - 1);
    const value = bytes / Math.pow(1024, i);
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${sizes[i]}`;
  };

  const handleFilesSelected = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (!files.length || !conversation?.id) {
      return;
    }

    if (documents.length + files.length > 5) {
      setUploadError('Max 5 PDFs per conversation.');
      return;
    }

    setUploadError('');
    setUploading(true);
    setUploadProgress(0);

    try {
      const response = await api.uploadDocuments(conversation.id, files, (progress) => {
        setUploadProgress(Math.round(progress * 100));
      });

      if (response?.errors?.length) {
        const errorText = response.errors.map(err => `${err.filename}: ${err.error}`).join(' | ');
        setUploadError(errorText);
      }

      const updatedDocuments = await api.listDocuments(conversation.id);
      setDocuments(updatedDocuments);
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadError('Failed to upload documents.');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!conversation?.id) return;
    try {
      await api.deleteDocument(conversation.id, documentId);
      const updatedDocuments = await api.listDocuments(conversation.id);
      setDocuments(updatedDocuments);
    } catch (error) {
      console.error('Failed to delete document:', error);
      setUploadError('Failed to remove document.');
    }
  };

  useEffect(() => {
    let timeout;
    if (copySuccess) {
      timeout = setTimeout(() => {
        setCopySuccess(false);
      }, 2000);
    }
    return () => clearTimeout(timeout);
  }, [copySuccess]);

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="header-info">
          <h3>{conversation.title || 'New Conversation'}</h3>
          <span className="model-info">{conversation.framework}</span>
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

      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <MessageItem key={index} msg={msg} />
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <div className="input-stack">
          <div className="upload-toolbar">
            <div className="upload-actions">
              <button
                type="button"
                className="upload-button"
                onClick={handleUploadClick}
                disabled={!conversation || uploading}
                aria-label="Attach PDF files"
                title="Attach PDF files"
              >
                <span>Attach PDFs</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                multiple
                onChange={handleFilesSelected}
                className="file-input"
              />
              <span className="upload-hint">Max 5 PDFs - 10MB each</span>
            </div>
            {uploading && (
              <div className="upload-progress">
                <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }} />
                <span>Uploading {uploadProgress}%</span>
              </div>
            )}
            {uploadError && <div className="upload-error">{uploadError}</div>}
          </div>

          {(documentsLoading || documents.length > 0) && (
            <div className="document-list">
              {documentsLoading && <div className="document-loading">Loading documents...</div>}
              {documents.map((doc) => (
                <div key={doc.id} className={`document-item status-${doc.status}`}>
                  <div className="document-meta">
                    <div className="document-name">{doc.filename}</div>
                    <div className="document-details">
                      {formatBytes(doc.size_bytes)}
                      {doc.page_count ? ` · ${doc.page_count} pages` : ''}
                    </div>
                    {doc.error_message && (
                      <div className="document-error">{doc.error_message}</div>
                    )}
                  </div>
                  <div className="document-actions">
                    <span className={`document-status status-${doc.status}`}>{doc.status}</span>
                    <button
                      type="button"
                      className="document-remove"
                      onClick={() => handleDeleteDocument(doc.id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="composer-row">
            <textarea
              ref={textareaRef}
              className="message-input"
              placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
            />
            <button
              type="submit"
              className="send-button"
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
              title="Send message (Enter)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
