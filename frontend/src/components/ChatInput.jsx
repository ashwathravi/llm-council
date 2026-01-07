
import React, { memo, useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Paperclip, Send, X, FileText, Loader2 } from "lucide-react";

const ChatInput = memo(({ conversationId, isLoading, onSendMessage }) => {
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  // Load documents
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
      // Reset height
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleUploadClick = () => {
    if (!conversationId || uploading) return;
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

    if (!files.length || !conversationId) return;

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
      setUploadError('Failed to remove document.');
    }
  };

  return (
    <div className="border-t bg-background p-4">
      <form onSubmit={handleSubmit} className="mx-auto max-w-3xl flex flex-col gap-3">
        {/* Upload Error */}
        {uploadError && (
          <div className="text-xs text-destructive bg-destructive/10 p-2 rounded">{uploadError}</div>
        )}

        {/* Document List */}
        {(documents.length > 0 || uploading) && (
          <div className="flex flex-wrap gap-2">
            {documents.map((doc) => (
              <Badge key={doc.id} variant="secondary" className="pl-2 pr-1 py-1 gap-2 h-7 font-normal">
                <FileText className="h-3 w-3 text-muted-foreground" />
                <span className="truncate max-w-[150px]">{doc.filename}</span>
                <span className="text-xs text-muted-foreground ml-1">{formatBytes(doc.size_bytes)}</span>
                <button
                  type="button"
                  onClick={() => handleDeleteDocument(doc.id)}
                  className="ml-1 rounded-full p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}

            {uploading && (
              <Badge variant="outline" className="animate-pulse">
                Uploading... {uploadProgress}%
              </Badge>
            )}
          </div>
        )}

        {/* Input Area */}
        <div className="relative flex items-end gap-2 rounded-lg border bg-background p-2 shadow-sm focus-within:ring-1 focus-within:ring-ring">
          {/* Attachment Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={handleUploadClick}
                  disabled={!conversationId || uploading}
                >
                  <Paperclip className="h-4 w-4" />
                  <span className="sr-only">Attach PDF</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Attach PDF (Max 5)</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={handleFilesSelected}
          />

          <Textarea
            ref={textareaRef}
            tabIndex={0}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message the Council..."
            spellCheck={false}
            className="min-h-[44px] w-full resize-none border-0 bg-transparent py-3 focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none"
            disabled={isLoading}
          />

          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || isLoading}
            className="h-9 w-9 shrink-0"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span className="sr-only">Send message</span>
          </Button>
        </div>
        <div className="text-xs text-muted-foreground text-center">
          Review Council responses carefully. AI can make mistakes.
        </div>
      </form>
    </div>
  );
});

export default ChatInput;
