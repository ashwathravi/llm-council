
import React, { memo } from 'react';
import { api } from '../api';
import { Button } from "@/components/ui/button";
import { Download, Link as LinkIcon, FileText, Check } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/use-toast";

const ChatHeader = memo(({ title, conversationId }) => {
  const { toast } = useToast();
  const [copied, setCopied] = React.useState(false);

  const handleExport = async (format) => {
    if (!conversationId) return;
    try {
      await api.exportConversation(conversationId, format);
      toast({
        title: "Export Started",
        description: `Exporting conversation to ${format.toUpperCase()}...`,
      });
    } catch (error) {
      console.error('Export failed:', error);
      toast({
        variant: "destructive",
        title: "Export Failed",
        description: "Could not export conversation.",
      });
    }
  };

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      toast({
        title: "Link Copied",
        description: "Conversation link copied to clipboard.",
      });
      setTimeout(() => setCopied(false), 2000);
    }).catch(err => {
      console.error('Failed to copy link:', err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to copy link.",
      });
    });
  };

  return (
    <div className="flex items-center justify-between px-6 py-4 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-10">
      <div>
        <h3 className="font-semibold text-lg leading-none tracking-tight">{title || 'New Conversation'}</h3>
      </div>
      <div className="flex items-center gap-1">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={() => handleExport('md')}>
                <FileText className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Export to Markdown</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={() => handleExport('pdf')}>
                <Download className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Export to PDF</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={handleCopyLink}>
                {copied ? <Check className="h-4 w-4 text-green-500" /> : <LinkIcon className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Copy Link</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
});

ChatHeader.displayName = 'ChatHeader';

export default ChatHeader;
