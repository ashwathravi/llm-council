
import React, { memo } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import CouncilMessageBlock from './CouncilMessageBlock';
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { User } from "lucide-react";

const MessageItem = memo(({ msg, messageIndex, onRetryFailedModels, onRefreshSynthesis }) => {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end mb-6">
        <div className="flex max-w-[80%] gap-3 flex-row-reverse">
          <Avatar className="h-8 w-8 mt-1">
            <AvatarFallback className="bg-slate-900 text-slate-50 dark:bg-slate-800 dark:text-slate-100">
              <User className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <div className="bg-slate-900 text-slate-50 dark:bg-slate-800 dark:text-slate-100 px-4 py-3 rounded-2xl rounded-tr-sm">
            <MarkdownRenderer
              content={msg.content}
              className="prose-invert prose-p:my-0 prose-headings:my-0 [&_*]:text-inherit"
            />
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message (Council Block)
  return (
    <div className="flex justify-start mb-8">
      <div className="max-w-[95%] w-full flex gap-3">
        <Avatar className="h-8 w-8 mt-1 border border-border">
          <AvatarFallback className="bg-background">
            🏛️
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium mb-1 ml-1 text-muted-foreground">LLM Council</div>
          <CouncilMessageBlock
            message={msg}
            messageIndex={messageIndex}
            onRetryFailedModels={onRetryFailedModels}
            onRefreshSynthesis={onRefreshSynthesis}
          />
        </div>
      </div>
    </div>
  );
});

MessageItem.displayName = 'MessageItem';

export default MessageItem;
