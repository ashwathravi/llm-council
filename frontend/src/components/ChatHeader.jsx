
import React, { memo } from 'react';
import { api } from '../api';
import { logger } from '@/lib/logger';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, Link as LinkIcon, FileText, Check, ClipboardList } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/use-toast";
import { getPrimaryArtifactCount, getSessionTypeLabel } from '@/lib/sessionMetadata';
import { getDesignTargetLabel, getStudioGoalLabel, normalizeSessionConfig } from '@/lib/designStudioConfig';
import { getSpecialistTemplateLabel } from '@/lib/specialistTemplates';

const FRAMEWORK_LABELS = {
  standard: 'Standard Council',
  debate: 'Chain of Debate',
  six_hats: 'Six Thinking Hats',
  ensemble: 'Ensemble (Fast)',
  heterogeneous: 'Heterogeneous Council',
};

const ChatHeader = memo(({
  title,
  conversationId,
  framework,
  sessionType,
  sessionConfig,
  specialistTemplateId,
  primaryArtifacts,
  councilModels,
  chairmanModel,
  navigatorItemCount = 0,
}) => {
  const { toast } = useToast();
  const [copied, setCopied] = React.useState(false);
  const selectedCount = Array.isArray(councilModels) ? councilModels.length : 0;
  const primaryArtifactCount = getPrimaryArtifactCount(primaryArtifacts);
  const frameworkLabel = FRAMEWORK_LABELS[framework] || framework || 'Standard Council';
  const sessionTypeLabel = getSessionTypeLabel(sessionType);
  const normalizedSessionConfig = normalizeSessionConfig(sessionType, sessionConfig);
  const specialistTemplateLabel = getSpecialistTemplateLabel(specialistTemplateId);
  const chairmanLabel = chairmanModel || 'Auto';
  const canExportDesignHandoff = sessionType === 'design_studio' && Boolean(normalizedSessionConfig.approved_direction_id);

  const handleExport = async (format) => {
    if (!conversationId) return;
    try {
      await api.exportConversation(conversationId, format);
      toast({
        title: "Export Started",
        description: `Exporting conversation to ${format.toUpperCase()}...`,
      });
    } catch (error) {
      logger.error('Export failed:', error);
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
      logger.error('Failed to copy link:', err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to copy link.",
      });
    });
  };

  return (
    <div className="flex items-center justify-between px-6 py-4 border-b bg-background/50 backdrop-blur-sm sticky top-0 z-10">
      <div className="space-y-2 min-w-0">
        <h3 className="font-semibold text-lg leading-none tracking-tight">{title || 'New Conversation'}</h3>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="secondary" className="text-xs">{sessionTypeLabel}</Badge>
          {sessionType === 'design_studio' && (
            <>
              <Badge variant="secondary" className="text-xs">{getDesignTargetLabel(normalizedSessionConfig.design_target)}</Badge>
              <Badge variant="secondary" className="text-xs">{getStudioGoalLabel(normalizedSessionConfig.studio_goal)}</Badge>
            </>
          )}
          {specialistTemplateLabel && <Badge variant="secondary" className="text-xs">{specialistTemplateLabel}</Badge>}
          <Badge variant="secondary" className="text-xs">{frameworkLabel}</Badge>
          <Badge variant="outline" className="text-xs">{selectedCount} models</Badge>
          <Badge variant="outline" className="text-xs">{primaryArtifactCount} artifacts</Badge>
          <Badge variant="outline" className="text-xs">Chairman: {chairmanLabel}</Badge>
          <Badge variant="outline" className="text-xs">{navigatorItemCount} turns</Badge>
        </div>
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

          {canExportDesignHandoff && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => handleExport('design_md')}>
                  <ClipboardList className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Export DESIGN.md</TooltipContent>
            </Tooltip>
          )}

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
