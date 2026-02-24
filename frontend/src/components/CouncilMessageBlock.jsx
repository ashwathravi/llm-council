
import { useMemo, useState, memo } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Trophy, Crown, BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";

// ⚡ Bolt: Memoize markdown rendering to prevent re-parsing on every parent re-render
const MarkdownContent = memo(({ content }) => (
  <MarkdownRenderer
    content={content}
    className="markdown-content text-foreground prose-p:text-foreground/90 prose-li:text-foreground/90 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-foreground dark:prose-code:text-foreground prose-code:bg-muted/80 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-slate-950 prose-pre:text-slate-100 prose-pre:border prose-pre:border-slate-800 prose-pre:rounded-lg prose-pre:px-4 prose-pre:py-3"
  />
));

MarkdownContent.displayName = 'MarkdownContent';

// ⚡ Bolt: Extract and memoize Rankings tab content to prevent re-renders when Stage 3 is streaming
const RankingsTabContent = memo(({ aggregateRankings }) => (
  <div className="p-6">
    <h3 className="font-semibold mb-4">Council Rankings</h3>
    <div className="space-y-4">
      {aggregateRankings.length > 0 ? (
        aggregateRankings.map((rank, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 border rounded-lg bg-card/50">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted font-bold">
                {idx + 1}
              </div>
              <div>
                <div className="font-medium">{rank.model}</div>
                <div className="text-xs text-muted-foreground">{rank.rankings_count} evaluations</div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-mono font-bold text-lg">{rank.average_rank}</div>
              <div className="text-xs text-muted-foreground">Avg Rank</div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-muted-foreground italic">No rankings available for this session type.</div>
      )}
    </div>
  </div>
));

RankingsTabContent.displayName = 'RankingsTabContent';

// ⚡ Bolt: Extract and memoize Stage 1 tab content to keep individual responses stable during updates
const Stage1TabContent = memo(({ res }) => (
  <div className="p-6">
    <div className="flex items-center gap-2 mb-4">
      <Badge variant="outline">{res.model}</Badge>
    </div>
    <MarkdownContent content={res.response} />
  </div>
));

Stage1TabContent.displayName = 'Stage1TabContent';

const formatModelList = (models) => {
  if (!Array.isArray(models) || models.length === 0) {
    return 'None';
  }
  return models.join(', ');
};

const CouncilMessageBlock = ({ message }) => {
  const { stage1, stage2, stage3, loading, errors, metadata } = message;
  const [activeTab, setActiveTab] = useState('consensus');

  const hasStage1 = stage1 && stage1.length > 0;
  const hasStage2 = stage2 && stage2.length > 0;
  const hasStage3 = stage3 && stage3.response;

  const aggregateRankings = metadata?.aggregate_rankings || [];

  const requestedCouncilModels = Array.isArray(metadata?.requested_council_models)
    ? metadata.requested_council_models
    : [];
  const effectiveCouncilModels = Array.isArray(metadata?.effective_council_models)
    ? metadata.effective_council_models
    : [];
  const respondedCouncilModels = Array.isArray(metadata?.responded_council_models)
    ? metadata.responded_council_models
    : hasStage1
      ? stage1.map((result) => result.model)
      : [];
  const stage1Errors = metadata?.stage1_errors;

  const combinedErrors = useMemo(() => {
    const merged = [];
    const seen = new Set();

    const pushError = (errorItem) => {
      if (!errorItem || typeof errorItem !== 'object') return;
      const model = errorItem.model || 'unknown';
      const error = errorItem.error || 'Unknown error';
      const key = `${model}:${error}`;
      if (seen.has(key)) return;
      seen.add(key);
      merged.push({ model, error });
    };

    if (Array.isArray(errors)) {
      errors.forEach(pushError);
    }
    if (Array.isArray(stage1Errors)) {
      stage1Errors.forEach(pushError);
    }

    return merged;
  }, [errors, stage1Errors]);

  const hasModelMetadata =
    Array.isArray(metadata?.requested_council_models) ||
    Array.isArray(metadata?.effective_council_models) ||
    Array.isArray(metadata?.responded_council_models);

  return (
    <Card className="w-full border-2 border-transparent data-[state=chairman]:border-chairman/20 overflow-hidden">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="bg-muted border-b px-4 py-2 flex items-center justify-between flex-wrap gap-2">
          <TabsList className="h-9 bg-background/80">
            <TabsTrigger value="consensus" className="gap-2">
              <Crown className="h-3.5 w-3.5 text-chairman" />
              Consensus
            </TabsTrigger>
            {hasStage2 && (
              <TabsTrigger value="rankings" className="gap-2">
                <Trophy className="h-3.5 w-3.5 text-yellow-500" />
                Rankings
              </TabsTrigger>
            )}
            {hasStage1 && stage1.map((res, idx) => (
              <TabsTrigger key={idx} value={`model-${idx}`} className="hidden sm:inline-flex">
                {res.model.split('/')[1] || res.model}
              </TabsTrigger>
            ))}
          </TabsList>

          {hasModelMetadata && (
            <div className="flex items-center gap-1 flex-wrap">
              <Badge variant="outline" className="text-[10px]">Requested {requestedCouncilModels.length}</Badge>
              <Badge variant="outline" className="text-[10px]">Effective {effectiveCouncilModels.length}</Badge>
              <Badge variant="outline" className="text-[10px]">Responded {respondedCouncilModels.length}</Badge>
            </div>
          )}
        </div>

        <div className="p-0">
          <TabsContent value="consensus" className="m-0 focus-visible:ring-0">
            <div className="p-6 min-h-[100px]">
              {hasStage3 ? (
                <>
                  <div className="flex items-center gap-2 mb-4 flex-wrap">
                    <Badge variant="outline" className="border-chairman text-chairman gap-1">
                      <Crown className="h-3 w-3" />
                      Chairman: {stage3.model}
                    </Badge>
                    {metadata?.framework && (
                      <Badge variant="secondary" className="text-xs">
                        {metadata.framework}
                      </Badge>
                    )}
                  </div>
                  {hasModelMetadata && (
                    <div className="mb-4 space-y-1 text-xs text-muted-foreground">
                      <div>
                        <span className="font-semibold text-foreground/80">Requested:</span> {formatModelList(requestedCouncilModels)}
                      </div>
                      <div>
                        <span className="font-semibold text-foreground/80">Effective:</span> {formatModelList(effectiveCouncilModels)}
                      </div>
                      <div>
                        <span className="font-semibold text-foreground/80">Responded:</span> {formatModelList(respondedCouncilModels)}
                      </div>
                    </div>
                  )}
                  <MarkdownContent content={stage3.response} />
                  {loading?.stage3 && <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center p-8 text-muted-foreground gap-3">
                  <BrainCircuit className="h-8 w-8 animate-pulse text-primary/50" />
                  <p>The Council is deliberating...</p>
                  <div className="flex gap-2 text-xs">
                    <span className={cn('transition-opacity', loading?.stage1 ? 'opacity-100 font-medium text-foreground' : 'opacity-50')}>Collecting Thoughts</span>
                    <span>→</span>
                    <span className={cn('transition-opacity', loading?.stage2 ? 'opacity-100 font-medium text-foreground' : 'opacity-50')}>Debating</span>
                    <span>→</span>
                    <span className={cn('transition-opacity', loading?.stage3 ? 'opacity-100 font-medium text-foreground' : 'opacity-50')}>Synthesizing</span>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="rankings" className="m-0 focus-visible:ring-0">
            <RankingsTabContent aggregateRankings={aggregateRankings} />
          </TabsContent>

          {hasStage1 && stage1.map((res, idx) => (
            <TabsContent key={idx} value={`model-${idx}`} className="m-0 focus-visible:ring-0">
              <Stage1TabContent res={res} />
            </TabsContent>
          ))}
        </div>

        {combinedErrors.length > 0 && (
          <div className="bg-destructive/10 p-4 border-t border-destructive/20 text-destructive text-sm">
            <div className="font-semibold flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4" />
              Errors detected:
            </div>
            <ul className="list-disc list-inside">
              {combinedErrors.map((err, idx) => (
                <li key={idx}><strong>{err.model}:</strong> {err.error}</li>
              ))}
            </ul>
          </div>
        )}
      </Tabs>
    </Card>
  );
};

export default CouncilMessageBlock;
