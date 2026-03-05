
import { useMemo, useState, memo } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { AlertTriangle, Trophy, Crown, BrainCircuit, GitCompareArrows, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";

// ⚡ Bolt: Memoize markdown rendering to prevent re-parsing on every parent re-render
const MarkdownContent = memo(({ content }) => (
  <MarkdownRenderer
    content={content}
    className="markdown-content text-foreground prose-p:text-foreground/90 prose-li:text-foreground/90 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-foreground dark:prose-code:text-foreground prose-code:bg-muted/80 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
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

const DiffTabContent = memo(({ diffData }) => {
  const { consensusSentences, overlaps, uniqueTerms } = diffData;

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <h3 className="font-semibold">Agreement Signals</h3>
        {consensusSentences.length > 0 ? (
          <div className="space-y-2">
            {consensusSentences.map((item, idx) => (
              <div key={idx} className="rounded-lg border bg-card/40 p-3">
                <div className="text-sm text-foreground/90">{item.sentence}</div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Supported by {item.supporters.length} models
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No strong sentence-level overlap detected between model responses.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="font-semibold">Pairwise Similarity</h3>
        {overlaps.length > 0 ? (
          <div className="space-y-3">
            {overlaps.map((item, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{item.left} vs {item.right}</span>
                  <span>{item.score}%</span>
                </div>
                <div className="h-2 w-full rounded bg-muted">
                  <div className="h-2 rounded bg-primary" style={{ width: `${item.score}%` }} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Not enough model responses to compare.</p>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="font-semibold">Distinctive Terms</h3>
        <div className="space-y-2">
          {uniqueTerms.map((item, idx) => (
            <div key={idx} className="rounded-lg border bg-card/40 p-3">
              <div className="text-xs font-medium text-foreground/80">{item.model}</div>
              <div className="mt-1 text-sm text-muted-foreground">
                {item.terms.length > 0 ? item.terms.join(', ') : 'No high-signal unique terms.'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

DiffTabContent.displayName = 'DiffTabContent';

const formatModelList = (models) => {
  if (!Array.isArray(models) || models.length === 0) {
    return 'None';
  }
  return models.join(', ');
};

const STOP_WORDS = new Set([
  'about', 'after', 'again', 'against', 'because', 'being', 'between', 'could',
  'does', 'doing', 'from', 'have', 'just', 'more', 'most', 'other', 'over',
  'should', 'their', 'there', 'these', 'this', 'those', 'under', 'very', 'with',
  'would', 'your', 'that', 'then', 'than', 'into', 'while', 'where', 'when',
  'which', 'what', 'will', 'also', 'only', 'such', 'each'
]);

const splitSentences = (text) => (
  String(text || '')
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length >= 30)
);

const normalizeSentence = (sentence) => (
  sentence
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
);

const tokenize = (text) => (
  String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((token) => token.length >= 4 && !STOP_WORDS.has(token))
);

const extractRetryModelName = (modelLabel) => {
  if (typeof modelLabel !== 'string') return '';
  const cleaned = modelLabel.trim();
  if (cleaned.endsWith(')') && cleaned.includes(' (')) {
    return cleaned.slice(0, cleaned.lastIndexOf(' (')).trim();
  }
  return cleaned;
};

const buildComparisonDiff = (stage1Results) => {
  if (!Array.isArray(stage1Results) || stage1Results.length < 2) {
    return { consensusSentences: [], overlaps: [], uniqueTerms: [] };
  }

  const modelEntries = stage1Results.map((item) => ({
    model: item.model,
    response: item.response || '',
    tokens: new Set(tokenize(item.response || '')),
  }));

  const tokenUsage = new Map();
  modelEntries.forEach((entry) => {
    entry.tokens.forEach((token) => {
      tokenUsage.set(token, (tokenUsage.get(token) || 0) + 1);
    });
  });

  const uniqueTerms = modelEntries.map((entry) => {
    const terms = [...entry.tokens]
      .filter((token) => tokenUsage.get(token) === 1)
      .sort()
      .slice(0, 8);
    return { model: entry.model, terms };
  });

  const overlaps = [];
  for (let i = 0; i < modelEntries.length; i += 1) {
    for (let j = i + 1; j < modelEntries.length; j += 1) {
      const left = modelEntries[i];
      const right = modelEntries[j];
      const [shorter, longer] = left.tokens.size <= right.tokens.size
        ? [left.tokens, right.tokens]
        : [right.tokens, left.tokens];

      let intersection = 0;
      shorter.forEach((token) => {
        if (longer.has(token)) intersection += 1;
      });

      const union = left.tokens.size + right.tokens.size - intersection;
      const score = union > 0 ? Math.round((intersection / union) * 100) : 0;
      overlaps.push({ left: left.model, right: right.model, score });
    }
  }
  overlaps.sort((a, b) => b.score - a.score);

  const sentenceSupport = new Map();
  stage1Results.forEach((item) => {
    const localSeen = new Set();
    splitSentences(item.response).forEach((sentence) => {
      const normalized = normalizeSentence(sentence);
      if (!normalized || localSeen.has(normalized)) return;
      localSeen.add(normalized);

      if (!sentenceSupport.has(normalized)) {
        sentenceSupport.set(normalized, {
          sentence,
          supporters: new Set([item.model]),
        });
        return;
      }

      sentenceSupport.get(normalized).supporters.add(item.model);
    });
  });

  const consensusSentences = [...sentenceSupport.values()]
    .filter((item) => item.supporters.size >= 2)
    .sort((a, b) => b.supporters.size - a.supporters.size)
    .slice(0, 5)
    .map((item) => ({
      sentence: item.sentence,
      supporters: [...item.supporters],
    }));

  return { consensusSentences, overlaps, uniqueTerms };
};

const CouncilMessageBlock = ({ message, messageIndex, onRetryFailedModels }) => {
  const { stage1, stage2, stage3, loading, errors, metadata } = message;
  const [activeTab, setActiveTab] = useState('consensus');
  const [isRetryingFailedModels, setIsRetryingFailedModels] = useState(false);
  const [retryingModels, setRetryingModels] = useState([]);
  const { toast } = useToast();

  const hasStage1 = stage1 && stage1.length > 0;
  const hasStage2 = stage2 && stage2.length > 0;
  const hasStage3 = stage3 && stage3.response;
  const hasComparisonDiff = hasStage1 && stage1.length > 1;

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

  const failedModelIds = useMemo(() => {
    const seen = new Set();
    const models = [];
    combinedErrors.forEach((errorItem) => {
      const normalized = extractRetryModelName(errorItem.model);
      if (!normalized || seen.has(normalized)) return;
      seen.add(normalized);
      models.push(normalized);
    });
    return models;
  }, [combinedErrors]);

  const diffData = useMemo(() => buildComparisonDiff(stage1), [stage1]);

  const hasModelMetadata =
    Array.isArray(metadata?.requested_council_models) ||
    Array.isArray(metadata?.effective_council_models) ||
    Array.isArray(metadata?.responded_council_models);

  const canRetryFailedModels = (
    typeof onRetryFailedModels === 'function' &&
    Number.isInteger(messageIndex) &&
    failedModelIds.length > 0
  );

  const handleRetryModels = async (modelsToRetry) => {
    if (!canRetryFailedModels || !Array.isArray(modelsToRetry) || modelsToRetry.length === 0) return;
    const uniqueModels = [...new Set(modelsToRetry.filter(Boolean))];
    const isBulkRetry = uniqueModels.length > 1;

    if (isBulkRetry) {
      if (isRetryingFailedModels) return;
      setIsRetryingFailedModels(true);
    } else {
      if (retryingModels.includes(uniqueModels[0])) return;
      setRetryingModels((prev) => [...prev, uniqueModels[0]]);
    }

    try {
      const retryResult = await onRetryFailedModels(messageIndex, uniqueModels);
      const recoveredModels = Array.isArray(retryResult?.recovered_models)
        ? retryResult.recovered_models
        : [];
      const failedModels = Array.isArray(retryResult?.failed_models)
        ? retryResult.failed_models
        : [];

      const title = failedModels.length > 0 ? 'Retry completed with some failures' : 'Retry completed';
      const description = [
        `Recovered: ${recoveredModels.length}`,
        `Still failing: ${failedModels.length}`,
      ].join(' • ');

      toast({
        title,
        description,
        variant: failedModels.length > 0 ? 'destructive' : 'default',
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Failed to retry models';
      toast({
        title: 'Retry failed',
        description: detail,
        variant: 'destructive',
      });
    } finally {
      if (isBulkRetry) {
        setIsRetryingFailedModels(false);
      } else {
        setRetryingModels((prev) => prev.filter((modelName) => modelName !== uniqueModels[0]));
      }
    }
  };

  const handleRetryFailedModels = async () => {
    await handleRetryModels(failedModelIds);
  };

  const handleRetrySingleModel = async (modelName) => {
    await handleRetryModels([modelName]);
  };

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
            {hasComparisonDiff && (
              <TabsTrigger value="diff" className="gap-2">
                <GitCompareArrows className="h-3.5 w-3.5 text-sky-500" />
                Diff
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

          <TabsContent value="diff" className="m-0 focus-visible:ring-0">
            <DiffTabContent diffData={diffData} />
          </TabsContent>

          {hasStage1 && stage1.map((res, idx) => (
            <TabsContent key={idx} value={`model-${idx}`} className="m-0 focus-visible:ring-0">
              <Stage1TabContent res={res} />
            </TabsContent>
          ))}
        </div>

        {combinedErrors.length > 0 && (
          <div className="bg-destructive/10 p-4 border-t border-destructive/20 text-destructive text-sm">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div className="font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Errors detected:
              </div>
              {canRetryFailedModels && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 border-destructive/40 text-destructive hover:text-destructive"
                  onClick={handleRetryFailedModels}
                  disabled={isRetryingFailedModels}
                >
                  <RotateCcw className={cn('mr-1 h-3.5 w-3.5', isRetryingFailedModels && 'animate-spin')} />
                  {isRetryingFailedModels ? 'Retrying...' : 'Retry Failed Models'}
                </Button>
              )}
            </div>
            <ul className="space-y-2">
              {combinedErrors.map((err, idx) => (
                <li key={idx} className="flex flex-col gap-2 rounded border border-destructive/20 bg-background/50 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <strong>{err.model}:</strong> {err.error}
                  </div>
                  {canRetryFailedModels && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 border-destructive/40 text-destructive hover:text-destructive"
                      onClick={() => handleRetrySingleModel(extractRetryModelName(err.model))}
                      disabled={isRetryingFailedModels || retryingModels.includes(extractRetryModelName(err.model))}
                    >
                      <RotateCcw className={cn('mr-1 h-3.5 w-3.5', retryingModels.includes(extractRetryModelName(err.model)) && 'animate-spin')} />
                      {retryingModels.includes(extractRetryModelName(err.model)) ? 'Retrying...' : 'Retry model'}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Tabs>
    </Card>
  );
};

export default CouncilMessageBlock;
