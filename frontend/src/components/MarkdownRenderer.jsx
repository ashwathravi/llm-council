import React, { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const Pre = ({ children, ...props }) => {
  const [copied, setCopied] = useState(false);

  // If pre doesn't contain code, just render it
  if (!children || children.type !== 'code') {
    return <pre {...props}>{children}</pre>;
  }

  // Extract text content from the code element's children
  // ReactMarkdown passes the text as children to the code element
  const codeContent = children.props.children;

  const handleCopy = () => {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(String(codeContent));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="relative group my-4 overflow-hidden rounded-lg border bg-muted">
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 bg-background/80 hover:bg-background shadow-sm backdrop-blur-sm"
            onClick={handleCopy}
            aria-label={copied ? "Copied" : "Copy code"}
        >
          {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
        </Button>
      </div>
      <pre {...props} className={cn("p-4 overflow-x-auto", props.className)}>
        {children}
      </pre>
    </div>
  );
};

const MarkdownRenderer = memo(({ content, className }) => {
  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none break-words [&_pre]:my-0 [&_pre]:bg-transparent [&_pre]:p-0 [&_pre]:border-0", className)}>
       <ReactMarkdown
          components={{
            pre: Pre,
            // eslint-disable-next-line no-unused-vars
            a: ({ node, ...props }) => (
              <a {...props} target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-500 transition-colors" />
            )
          }}
       >
         {content}
       </ReactMarkdown>
    </div>
  );
});

MarkdownRenderer.displayName = 'MarkdownRenderer';

export default MarkdownRenderer;
