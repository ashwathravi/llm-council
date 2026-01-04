import React, { memo, useState, useEffect, useRef } from 'react';
import { api } from '../api';
import './ChatInterface.css';

const ChatInput = memo(({ conversationId, isLoading, onSendMessage }) => {
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  // Load documents when conversation changes
  useEffect(() => {
    setUploadError('');
    setUploading(false);
    setUploadProgress(0);
    if (!conversationId) {
      setDocuments([]);
      setDocumentsLoading(false);
      return;
    }

    const loadDocuments = async () => {
      setDocumentsLoading(true);
      try {
        const docs = await api.listDocuments(conversationId);
        setDocuments(docs);
      } catch (error) {
        console.error('Failed to load documents:', error);
      } finally {
        setDocumentsLoading(false);
      }
    };

    loadDocuments();
  }, [conversationId]);

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
    if (!files.length || !conversationId) {
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
      const response = await api.uploadDocuments(conversationId, files, (progress) => {
        setUploadProgress(Math.round(progress * 100));
      });

      if (response?.errors?.length) {
        const errorText = response.errors.map(err => `${err.filename}: ${err.error}`).join(' | ');
        setUploadError(errorText);
      }

      const updatedDocuments = await api.listDocuments(conversationId);
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
    if (!conversationId) return;
    try {
      await api.deleteDocument(conversationId, documentId);
      const updatedDocuments = await api.listDocuments(conversationId);
      setDocuments(updatedDocuments);
    } catch (error) {
      console.error('Failed to delete document:', error);
      setUploadError('Failed to remove document.');
    }
  };

  return (
    <form className="input-form" onSubmit={handleSubmit}>
      <div className="input-stack">
        <div className="upload-toolbar">
          <div className="upload-actions">
            <button
              type="button"
              className="upload-button"
              onClick={handleUploadClick}
              disabled={!conversationId || uploading}
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
                    aria-label={`Remove ${doc.filename}`}
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
            aria-label="Chat input"
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
  );
});

export default ChatInput;
