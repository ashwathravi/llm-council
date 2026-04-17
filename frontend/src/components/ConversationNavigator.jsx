import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { NAVIGATOR_STATUS_META } from '@/lib/conversationNavigator';

const filterOutlineItems = (items, query) => {
  const normalizedQuery = String(query || '').trim().toLowerCase();
  if (!normalizedQuery) return items;

  return items.filter((item) => {
    const turnLabel = `turn ${item.turnNumber}`.toLowerCase();
    const snippet = String(item.snippet || '').toLowerCase();
    return turnLabel.includes(normalizedQuery) || snippet.includes(normalizedQuery);
  });
};

const ConversationNavigator = ({
  items = [],
  activeAnchorId,
  onJumpToTop,
  onJumpToAnchor,
  onJumpToFirst,
  onJumpToLatest,
  onClose,
  className,
}) => {
  const [query, setQuery] = useState('');

  const filteredItems = useMemo(() => filterOutlineItems(items, query), [items, query]);

  return (
    <div className={cn('flex h-full min-h-0 flex-col', className)}>
      <div className="border-b p-4 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">Conversation Navigator</h3>
            <p className="text-xs text-muted-foreground">
              Jump to user turns quickly.
            </p>
          </div>
          {typeof onClose === 'function' && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="Close conversation navigator"
            >
              Close
            </Button>
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter turns..."
            className="pl-8"
            aria-label="Filter conversation turns"
          />
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onJumpToTop}
            disabled={items.length === 0}
            className="w-full"
            aria-label="Jump to top"
          >
            Top
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onJumpToFirst}
            disabled={items.length === 0}
            className="w-full"
            aria-label="Jump to first turn"
          >
            <ArrowUp className="mr-1 h-3.5 w-3.5" />
            First
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onJumpToLatest}
            className="w-full"
            aria-label="Jump to latest turn"
          >
            <ArrowDown className="mr-1 h-3.5 w-3.5" />
            Latest
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-2 p-3">
          {items.length === 0 && (
            <div className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
              No turns yet. Start a conversation to build the navigator.
            </div>
          )}

          {items.length > 0 && filteredItems.length === 0 && (
            <div className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
              No turns match your filter.
            </div>
          )}

          {filteredItems.map((item) => {
            const statusMeta = NAVIGATOR_STATUS_META[item.status] || NAVIGATOR_STATUS_META.complete;
            const isActive = item.anchorId === activeAnchorId;
            return (
              <button
                key={item.anchorId}
                type="button"
                className={cn(
                  'w-full rounded-md border p-3 text-left transition-colors',
                  isActive ? 'border-primary bg-primary/10' : 'border-border hover:bg-accent/40'
                )}
                onClick={() => onJumpToAnchor(item.anchorId)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onJumpToAnchor(item.anchorId);
                  }
                }}
                aria-label={`Jump to turn ${item.turnNumber}`}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Turn {item.turnNumber}
                  </span>
                  <Badge variant="outline" className={cn('text-[10px]', statusMeta.className)}>
                    {statusMeta.label}
                  </Badge>
                </div>
                <p className="text-sm text-foreground/90">{item.snippet}</p>
              </button>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
};

export default ConversationNavigator;
