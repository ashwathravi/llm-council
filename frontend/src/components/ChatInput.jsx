import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import { logger } from '@/lib/logger';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { FileImage, FileText, Loader2, Paperclip, Send, X } from "lucide-react";
import { getPrimaryArtifactCount, getSessionTypeLabel, SESSION_TYPE_PLACEHOLDERS } from '@/lib/sessionMetadata';

const ChatInput = memo(({
  conversationId,
  sessionType = 'general',
  primaryArtifacts = [],
  isLoading,
  onSendMessage,
  onConversationRefresh,
}) => {
  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const isVisualReview = sessionType === 'visual_review';
  const isCodeReview = sessionType === 'code_review';
  const artifactKind = isVisualReview ? 'image' : isCodeReview ? 'code' : 'document';
  const uploadLabel = isVisualReview ? 'images' : isCodeReview ? 'code files' : 'PDFs';
  const uploadLimit = isCodeReview ? 10 : 5;
  const primaryArtifactCount = getPrimaryArtifactCount(primaryArtifacts);
  const sessionTypeLabel = getSessionTypeLabel(sessionType);
  const inputPlaceholder = SESSION_TYPE_PLACEHOLDERS[sessionType] || SESSION_TYPE_PLACEHOLDERS.general;
  const displayedArtifacts = useMemo(
    () => (Array.isArray(primaryArtifacts) ? primaryArtifacts : []).filter((artifact) =>
      artifact?.kind === artifactKind
    ),
    [artifactKind, primaryArtifacts]
  );

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

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

    if (displayedArtifacts.length + files.length > uploadLimit) {
      setUploadError(`Max ${uploadLimit} ${uploadLabel} per session.`);
      return;
    }

    setUploadError('');
    setUploading(true);
    setUploadProgress(0);

    try {
      const upload = isVisualReview
        ? api.uploadImageArtifacts
        : isCodeReview
          ? api.uploadCodeArtifacts
          : api.uploadDocuments;
      const response = await upload(conversationId, files, (progress) => {
        setUploadProgress(Math.round(progress * 100));
      });

      if (response?.errors?.length) {
        const errorText = response.errors.map(err => `${err.filename}: ${err.error}`).join(' | ');
        setUploadError(errorText);
      }

      await onConversationRefresh?.();
    } catch (error) {
      logger.error('Upload failed:', error);
      setUploadError(error instanceof Error ? error.message : `Failed to upload ${uploadLabel}.`);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteArtifact = async (artifact) => {
    if (!conversationId) return;
    try {
      if (isVisualReview) {
        await api.deleteImageArtifact(conversationId, artifact.id);
      } else if (isCodeReview) {
        await api.deleteCodeArtifact(conversationId, artifact.id);
      } else if (artifact?.document_id) {
        await api.deleteDocument(conversationId, artifact.document_id);
      }
      await onConversationRefresh?.();
    } catch (error) {
      logger.error('Failed to remove artifact:', error);
      setUploadError(`Failed to remove ${isVisualReview ? 'image' : isCodeReview ? 'code artifact' : 'document'}.`);
    }
  };

  return (
    <div className="border-t bg-background p-4">
      <form onSubmit={handleSubmit} className="mx-auto max-w-3xl flex flex-col gap-3">
        <div className="text-xs text-muted-foreground text-center">
          {sessionTypeLabel} workspace • {primaryArtifactCount} tracked artifacts
        </div>
        {/* Upload Error */}
        {uploadError && (
          <div className="text-xs text-destructive bg-destructive/10 p-2 rounded">{uploadError}</div>
        )}

        {/* Artifact List */}
        {(displayedArtifacts.length > 0 || uploading) && (
          <TooltipProvider>
            <div className="flex flex-wrap gap-2">
              {displayedArtifacts.map((artifact) => (
                isVisualReview ? (
                  <div key={artifact.id} className="group relative h-20 w-20 overflow-hidden rounded-md border bg-muted/20">
                    {artifact.preview_url ? (
                      <img
                        src={api.resolveUrl(artifact.preview_url)}
                        alt={artifact.label || artifact.filename || 'Uploaded image'}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                        <FileImage className="h-5 w-5" />
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDeleteArtifact(artifact)}
                      className="absolute right-1 top-1 rounded-full bg-background/90 p-1 text-foreground shadow-sm opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label={`Remove ${artifact.label || artifact.filename || 'image'}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <Badge key={artifact.id} variant="secondary" className="pl-2 pr-1 py-1 gap-2 h-7 font-normal">
                    <FileText className="h-3 w-3 text-muted-foreground" />
                    <span className="truncate max-w-[150px]">{artifact.label || artifact.filename}</span>
                    <span className="text-xs text-muted-foreground ml-1">
                      {isCodeReview
                        ? (artifact.summary || formatBytes(artifact.size_bytes))
                        : formatBytes(artifact.size_bytes)}
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          onClick={() => handleDeleteArtifact(artifact)}
                          className="ml-1 rounded-full p-0.5 hover:bg-slate-200 dark:hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          aria-label={`Remove ${artifact.label || artifact.filename}`}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>{isCodeReview ? 'Remove code artifact' : 'Remove document'}</TooltipContent>
                    </Tooltip>
                  </Badge>
                )
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
                  <span className="sr-only">
                    {isVisualReview ? 'Attach image artifact' : isCodeReview ? 'Attach code artifact' : 'Attach PDF artifact'}
                  </span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {!conversationId
                  ? "Start a session to attach files"
                  : uploading
                    ? "Uploading..."
                    : isVisualReview
                      ? "Attach image artifact (Max 5)"
                      : isCodeReview
                        ? "Attach code artifact (Max 10)"
                      : "Attach PDF artifact (Max 5)"}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <input
            ref={fileInputRef}
            type="file"
            accept={
              isVisualReview
                ? 'image/png,image/jpeg,image/gif,image/webp'
                : isCodeReview
                  ? '.c,.cc,.cpp,.cs,.css,.diff,.go,.h,.hpp,.html,.java,.js,.json,.jsx,.kt,.md,.mjs,.php,.py,.rb,.rs,.sh,.sql,.swift,.toml,.ts,.tsx,.txt,.yaml,.yml'
                  : 'application/pdf'
            }
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
            placeholder={inputPlaceholder}
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
