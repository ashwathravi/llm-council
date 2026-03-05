
import React, { memo, useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Paperclip, Send, X, FileText, Loader2 } from "lucide-react";

const PROMPT_SNIPPETS = [
  {
    id: 'decision-brief',
    label: 'Decision Brief',
    prompt: 'Give me a concise decision brief with options, trade-offs, and a recommended next step.'
  },
  {
    id: 'debug-plan',
    label: 'Debug Plan',
    prompt: 'Diagnose this issue step-by-step and propose the fastest path to a verified fix.'
  },
  {
    id: 'risk-scan',
    label: 'Risk Scan',
    prompt: 'Perform a risk scan: list key risks, likelihood, impact, and practical mitigations.'
  }
];

const DRAFT_STORAGE_KEY_PREFIX = 'llm-council:draft:';

const ChatInput = memo(({ conversationId, isLoading, onSendMessage, prefilledPrompt = '' }) => {
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');
  const [draftRestored, setDraftRestored] = useState(false);

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
    setDraftRestored(false);

    if (!conversationId) {
      setDocuments([]);
      setInput('');
      return;
    }

    const loadDocuments = async () => {
      try {
        const docs = await api.listDocuments(conversationId);
        setDocuments(docs);
      } catch (error) {
        console.error('Failed to load documents:', error);
      }
    };

    loadDocuments();
  }, [conversationId]);

  useEffect(() => {
    if (!conversationId) return;

    const storageKey = `${DRAFT_STORAGE_KEY_PREFIX}${conversationId}`;
    const savedDraft = localStorage.getItem(storageKey);
    if (savedDraft) {
      setInput(savedDraft);
      setDraftRestored(true);
    }
  }, [conversationId]);

  useEffect(() => {
    if (!conversationId) return;

    const storageKey = `${DRAFT_STORAGE_KEY_PREFIX}${conversationId}`;
    const trimmedInput = input.trim();

    if (!trimmedInput) {
      localStorage.removeItem(storageKey);
      return;
    }

    localStorage.setItem(storageKey, input);
  }, [conversationId, input]);

  useEffect(() => {
    if (!prefilledPrompt) return;
    setInput(prefilledPrompt);
    textareaRef.current?.focus();
  }, [prefilledPrompt]);

  useEffect(() => {
    const focusComposer = (event) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k') return;
      event.preventDefault();
      textareaRef.current?.focus();
    };

    window.addEventListener('keydown', focusComposer);
    return () => window.removeEventListener('keydown', focusComposer);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      if (conversationId) {
        localStorage.removeItem(`${DRAFT_STORAGE_KEY_PREFIX}${conversationId}`);
      }
      setDraftRestored(false);
      setInput('');
      // Reset height
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e) => {
    const isPrimaryModifierEnter = (e.ctrlKey || e.metaKey) && e.key === 'Enter';
    const isStandardSend = e.key === 'Enter' && !e.shiftKey;

    if (isStandardSend || isPrimaryModifierEnter) {
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
    } catch {
      setUploadError('Failed to remove document.');
    }
  };

  const handleSnippetSelect = (prompt) => {
    if (isLoading) return;
    setInput(prompt);
    textareaRef.current?.focus();
  };

  const handleClearDraft = () => {
    if (!conversationId) return;
    localStorage.removeItem(`${DRAFT_STORAGE_KEY_PREFIX}${conversationId}`);
    setInput('');
    setDraftRestored(false);
    textareaRef.current?.focus();
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
          <TooltipProvider>
            <div className="flex flex-wrap gap-2">
              {documents.map((doc) => (
                <Badge key={doc.id} variant="secondary" className="pl-2 pr-1 py-1 gap-2 h-7 font-normal">
                  <FileText className="h-3 w-3 text-muted-foreground" />
                  <span className="truncate max-w-[150px]">{doc.filename}</span>
                  <span className="text-xs text-muted-foreground ml-1">{formatBytes(doc.size_bytes)}</span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => handleDeleteDocument(doc.id)}
                        className="ml-1 rounded-full p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-label={`Remove ${doc.filename}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Remove document</TooltipContent>
                  </Tooltip>
                </Badge>
              ))}

              {uploading && (
                <Badge variant="outline" className="animate-pulse">
                  Uploading... {uploadProgress}%
                </Badge>
              )}
            </div>
          </TooltipProvider>
        )}

        {/* Input Area */}
        {draftRestored && (
          <div className="flex items-center justify-between rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
            <span>Draft restored for this conversation.</span>
            <Button type="button" variant="ghost" size="sm" onClick={handleClearDraft} className="h-6 px-2 text-xs">
              Clear draft
            </Button>
          </div>
        )}

        <div className="flex flex-wrap gap-2" aria-label="Prompt starter snippets">
          {PROMPT_SNIPPETS.map((snippet) => (
            <Button
              key={snippet.id}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleSnippetSelect(snippet.prompt)}
              disabled={isLoading}
              className="h-7 rounded-full text-xs"
              aria-label={`Insert ${snippet.label} snippet`}
            >
              {snippet.label}
            </Button>
          ))}
        </div>

        <div className="relative flex items-end gap-2 rounded-lg border bg-background p-2 shadow-sm focus-within:ring-1 focus-within:ring-ring">
          {/* Attachment Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground",
                    (!conversationId || uploading) && "opacity-50 cursor-not-allowed"
                  )}
                  onClick={(e) => {
                    if (!conversationId || uploading) {
                      e.preventDefault();
                      return;
                    }
                    handleUploadClick();
                  }}
                  aria-disabled={!conversationId || uploading}
                >
                  <Paperclip className="h-4 w-4" />
                  <span className="sr-only">Attach PDF</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {!conversationId
                  ? "Start a conversation to attach files"
                  : uploading
                    ? "Uploading..."
                    : "Attach PDF (Max 5)"}
              </TooltipContent>
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
            placeholder="Message the Council... (Ctrl/Cmd+K to focus)"
            aria-label="Message input"
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
