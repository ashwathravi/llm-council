
import { useMemo, useState, memo } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Trophy, Crown, BrainCircuit, CheckCircle2, FileImage, GitCompareArrows, PauseCircle, RefreshCw, RotateCcw, Wrench, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { buildDesignStudioWorkspaceView, formatDesignStudioScore } from "@/lib/designStudioWorkspace";
import { buildVisualReviewSurface } from "@/lib/visualReviewSurface";
import VisualReviewPanel from './VisualReviewPanel';

// ⚡ Bolt: Memoize markdown rendering to prevent re-parsing on every parent re-render
const MarkdownContent = memo(({ content }) => (
  <MarkdownRenderer
    content={content}
    className="markdown-content text-foreground prose-p:text-foreground/90 prose-li:text-foreground/90 prose-headings:text-foreground prose-strong:text-foreground prose-code:text-foreground dark:prose-code:text-foreground prose-code:bg-muted/80 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
  />
));

MarkdownContent.displayName = 'MarkdownContent';

const formatScore = (value) => (
  typeof value === 'number'
    ? value.toFixed(1).replace(/\.0$/, '')
    : 'n/a'
);

const rubricToneClass = (score) => {
  if (typeof score !== 'number') return 'border-border bg-muted/50 text-muted-foreground';
  if (score >= 4) return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
  if (score >= 3) return 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300';
  return 'border-destructive/30 bg-destructive/10 text-destructive';
};

const EMPTY_LIST = [];

const executionToneClass = (status) => {
  if (status === 'passed' || status === 'completed' || status === 'applied') {
    return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
  }
  if (status === 'failed') {
    return 'border-destructive/30 bg-destructive/10 text-destructive';
  }
  return 'border-border bg-muted/50 text-muted-foreground';
};

// ⚡ Bolt: Extract and memoize Rankings tab content to prevent re-renders when Stage 3 is streaming
const RankingsTabContent = memo(({ aggregateRankings, aggregateRubrics, framework, modelWeightProfile }) => {
  const profileByModel = new Map(
    (Array.isArray(modelWeightProfile) ? modelWeightProfile : [])
      .filter((entry) => entry && typeof entry.model === 'string')
      .map((entry) => [entry.model, entry])
  );
  const rubricByModel = new Map(
    (Array.isArray(aggregateRubrics) ? aggregateRubrics : [])
      .filter((entry) => entry && typeof entry.model === 'string')
      .map((entry) => [entry.model, entry])
  );

  return (
    <div className="p-6">
      <h3 className="font-semibold mb-2">Council Rankings</h3>
      {framework === 'heterogeneous' && (
        <p className="mb-4 text-sm text-muted-foreground">
          Rankings use confidence-weighted ballots multiplied by each model&apos;s rolling council performance.
        </p>
      )}
      <div className="space-y-4">
        {aggregateRankings.length > 0 ? (
          aggregateRankings.map((rank, idx) => {
            const profile = profileByModel.get(rank.model);
            const rubric = rubricByModel.get(rank.model);
            const topSpread = Array.isArray(rubric?.criteria)
              ? [...rubric.criteria]
                .filter((item) => typeof item?.spread === 'number' && item.spread > 0)
                .sort((left, right) => right.spread - left.spread)[0]
              : null;

            return (
              <div key={idx} className="rounded-lg border bg-card/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <div className="font-medium">{rank.model}</div>
                      <div className="text-xs text-muted-foreground">
                        {rank.rankings_count} evaluations
                        {rank.total_weight ? ` • total weight ${rank.total_weight}` : ''}
                      </div>
                      {framework === 'heterogeneous' && profile && (
                        <div className="text-xs text-muted-foreground">
                          Next weight {profile.dynamic_weight} • performance {profile.average_performance}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-bold text-lg">{rank.average_rank}</div>
                    <div className="text-xs text-muted-foreground">
                      {framework === 'heterogeneous' ? 'Weighted Avg Rank' : 'Avg Rank'}
                    </div>
                  </div>
                </div>

                {rubric && Array.isArray(rubric.criteria) && rubric.criteria.length > 0 && (
                  <div className="mt-4 space-y-3 border-t border-border/60 pt-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                      <Badge variant="outline">Rubric {formatScore(rubric.overall_score)}/5</Badge>
                      <span>{rubric.evaluation_count} scorecards</span>
                      {topSpread && (
                        <span>Highest disagreement: {topSpread.label} spread {formatScore(topSpread.spread)}</span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {rubric.criteria.map((criterion) => (
                        <div
                          key={`${rank.model}-${criterion.key}`}
                          className={cn(
                            'rounded-full border px-2.5 py-1 text-xs font-medium',
                            rubricToneClass(criterion.average_score)
                          )}
                        >
                          {criterion.label} {formatScore(criterion.average_score)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="text-muted-foreground italic">No rankings available for this session type.</div>
        )}
      </div>
    </div>
  );
});

const ExecutionTabContent = memo(({ execution }) => {
  const candidatePatch = execution?.candidate_patch || {};
  const checks = Array.isArray(execution?.checks) ? execution.checks : EMPTY_LIST;
  const summary = execution?.summary || {};

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="secondary">{execution?.mode || 'execution'}</Badge>
        <Badge variant="outline">Status: {execution?.status || 'unknown'}</Badge>
        {checks.length > 0 && (
          <>
            <Badge variant="outline">{summary.passed || 0} passed</Badge>
            <Badge variant="outline">{summary.failed || 0} failed</Badge>
            <Badge variant="outline">{summary.skipped || 0} skipped</Badge>
          </>
        )}
      </div>

      {execution?.reason && (
        <div className="rounded-md border bg-card/60 p-3 text-sm text-muted-foreground">
          {execution.reason}
        </div>
      )}

      <div className="space-y-2 rounded-md border bg-card/60 p-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h3 className="font-semibold">Candidate Patch</h3>
          <Badge className={cn('border', executionToneClass(candidatePatch?.status))}>
            {candidatePatch?.status || 'not_attempted'}
          </Badge>
        </div>
        {Array.isArray(candidatePatch?.changed_files) && candidatePatch.changed_files.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {candidatePatch.changed_files.map((file) => (
              <Badge key={file} variant="outline">{file}</Badge>
            ))}
          </div>
        )}
        {candidatePatch?.error && (
          <p className="text-sm text-destructive">{candidatePatch.error}</p>
        )}
        {candidatePatch?.excerpt && (
          <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs text-foreground">
            <code>{candidatePatch.excerpt}</code>
          </pre>
        )}
      </div>

      <div className="space-y-3">
        <h3 className="font-semibold">Checks</h3>
        {checks.length === 0 ? (
          <div className="rounded-md border bg-card/60 p-4 text-sm text-muted-foreground">
            No checks were recorded for this run.
          </div>
        ) : (
          checks.map((check, index) => {
            const status = check?.status || 'unknown';
            const Icon = status === 'passed' ? CheckCircle2 : status === 'failed' ? XCircle : PauseCircle;
            return (
              <div key={`${check?.label || check?.command || 'check'}-${index}`} className="rounded-md border bg-card/60 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-medium">{check?.label || check?.command || 'Check'}</div>
                    {check?.command && <div className="mt-1 text-xs text-muted-foreground">{check.command}</div>}
                  </div>
                  <Badge className={cn('border gap-1', executionToneClass(status))}>
                    <Icon className="h-3 w-3" />
                    {status}
                  </Badge>
                </div>
                {check?.output && (
                  <pre className="mt-3 overflow-x-auto rounded-md bg-muted p-3 text-xs text-foreground">
                    <code>{check.output}</code>
                  </pre>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
});

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

const DiffTabContent = memo(({ diffData, rubricHotspots }) => {
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
        <h3 className="font-semibold">Rubric Hotspots</h3>
        {rubricHotspots.length > 0 ? (
          <div className="space-y-2">
            {rubricHotspots.map((item, idx) => (
              <div key={idx} className="rounded-lg border bg-card/40 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">{item.model}</div>
                    <div className="text-xs text-muted-foreground">{item.label}</div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div>Avg {formatScore(item.averageScore)}/5</div>
                    <div>Spread {formatScore(item.spread)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Rubric scoring did not surface meaningful disagreement hotspots.
          </p>
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

const DESIGN_HANDOFF_KEYS = ['rationale', 'component_map', 'handoff_notes', 'open_questions'];

const getHandoffSection = (handoff, key) => {
  const directSection = handoff?.[key];
  if (directSection && typeof directSection === 'object') {
    return {
      label: directSection.label || key,
      content: typeof directSection.content === 'string' ? directSection.content : '',
      items: Array.isArray(directSection.items) ? directSection.items : EMPTY_LIST,
    };
  }

  const section = Array.isArray(handoff?.sections)
    ? handoff.sections.find((item) => item?.key === key)
    : null;
  if (!section) return null;

  return {
    label: section.label || key,
    content: typeof section.content === 'string' ? section.content : '',
    items: Array.isArray(section.items) ? section.items : EMPTY_LIST,
  };
};

const hasHandoffSectionContent = (section) => (
  Boolean(section && (section.content.trim() || section.items.length > 0))
);

const HandoffSectionContent = ({ section }) => {
  if (!section) return null;
  if (section.items.length > 0) {
    return (
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground/85">
        {section.items.map((item, index) => (
          <li key={`${section.label}-${index}`}>{item}</li>
        ))}
      </ul>
    );
  }

  if (section.content.trim()) {
    return (
      <div className="mt-2 text-sm">
        <MarkdownContent content={section.content} />
      </div>
    );
  }

  return (
    <p className="mt-2 text-sm text-muted-foreground">No detail captured.</p>
  );
};

const DesignStudioHandoffPanel = memo(({ handoff }) => {
  if (!handoff || handoff.status !== 'ready') return null;

  const selectedRef = handoff.selected_direction_ref && typeof handoff.selected_direction_ref === 'object'
    ? handoff.selected_direction_ref
    : null;
  const selectedSection = getHandoffSection(handoff, 'selected_direction');
  const sections = DESIGN_HANDOFF_KEYS
    .map((key) => getHandoffSection(handoff, key))
    .filter(hasHandoffSectionContent);
  const hasContent = Boolean(selectedRef) || hasHandoffSectionContent(selectedSection) || sections.length > 0;

  if (!hasContent) return null;

  return (
    <div className="mb-5 overflow-hidden rounded-xl border border-sky-500/20 bg-gradient-to-br from-sky-500/10 via-card to-emerald-500/10">
      <div className="border-b border-sky-500/10 px-4 py-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-300" />
              Structured design handoff
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Normalized from the final synthesis for implementation handoff.
            </p>
          </div>
          {handoff.selected_direction_id && (
            <Badge variant="outline" className="bg-background/70 text-xs">
              {handoff.selected_direction_id}
            </Badge>
          )}
        </div>
      </div>

      <div className="space-y-4 p-4">
        {selectedRef && (
          <div className="rounded-lg border bg-background/60 p-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="font-medium">{selectedRef.label || 'Selected direction'}</div>
              {selectedRef.source_model && (
                <Badge variant="secondary" className="text-[10px]">
                  {selectedRef.source_model}
                </Badge>
              )}
            </div>
            {selectedRef.summary && (
              <p className="mt-2 text-sm text-muted-foreground">{selectedRef.summary}</p>
            )}
          </div>
        )}

        {hasHandoffSectionContent(selectedSection) && (
          <div className="rounded-lg border bg-background/60 p-3">
            <h3 className="text-sm font-semibold">{selectedSection.label}</h3>
            <HandoffSectionContent section={selectedSection} />
          </div>
        )}

        {sections.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {sections.map((section) => (
              <div key={section.label} className="rounded-lg border bg-background/60 p-3">
                <h3 className="text-sm font-semibold">{section.label}</h3>
                <HandoffSectionContent section={section} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

HandoffSectionContent.displayName = 'HandoffSectionContent';
DesignStudioHandoffPanel.displayName = 'DesignStudioHandoffPanel';

const designWorkspaceStatusCopy = {
  empty: 'Waiting for candidate directions',
  single: 'One viable direction',
  pending: 'Comparison pending',
  complete: 'Comparison complete',
};

const DesignStudioWorkspacePanel = memo(({
  designStudio,
  stage1Errors,
  approvedDirectionId,
  onApproveDesignDirection,
}) => {
  const workspace = useMemo(
    () => buildDesignStudioWorkspaceView(designStudio, stage1Errors),
    [designStudio, stage1Errors]
  );
  const [approvingDirectionId, setApprovingDirectionId] = useState(null);

  if (!designStudio) return null;

  const selectedLabel = workspace.selectedCard?.label || workspace.selectedDirectionId || 'No leading direction';
  const canApprove = typeof onApproveDesignDirection === 'function';

  const handleApprove = async (directionId) => {
    if (!canApprove || !directionId || approvingDirectionId) return;
    setApprovingDirectionId(directionId);
    try {
      await onApproveDesignDirection(directionId);
    } finally {
      setApprovingDirectionId(null);
    }
  };

  return (
    <div className="mb-5 overflow-hidden rounded-xl border border-violet-500/20 bg-background">
      <div className="border-b bg-muted/40 px-4 py-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <GitCompareArrows className="h-4 w-4 text-violet-600 dark:text-violet-300" />
              Design Studio workspace
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Candidate directions, comparison status, and current selection.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="secondary" className="text-xs">
              {designWorkspaceStatusCopy[workspace.status] || workspace.comparisonStatus}
            </Badge>
            <Badge variant="outline" className="text-xs">
              {workspace.candidateCards.length} variants
            </Badge>
            {workspace.selectedCard && (
              <Badge variant="outline" className="text-xs">
                Leading: {selectedLabel}
              </Badge>
            )}
            {approvedDirectionId && (
              <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-xs text-emerald-700 dark:text-emerald-300">
                Approved: {approvedDirectionId}
              </Badge>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4 p-4">
        {workspace.hasPartialFailures && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-900 dark:text-amber-100">
            <div className="mb-2 flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              Partial run
            </div>
            <div className="space-y-1">
              {workspace.failedVariants.map((failure, index) => (
                <div key={`${failure.model}-${index}`}>
                  <span className="font-medium">{failure.model}:</span> {failure.error}
                </div>
              ))}
            </div>
          </div>
        )}

        {workspace.status === 'empty' ? (
          <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-sm text-muted-foreground">
            No candidate directions have arrived yet.
          </div>
        ) : (
          <>
            <div className="text-sm text-muted-foreground">
              {workspace.hasComparison
                ? workspace.status === 'complete'
                  ? 'Aggregate scoring is available across the viable directions.'
                  : 'Multiple viable directions are available; aggregate comparison has not completed yet.'
                : 'Waiting for another viable direction before aggregate comparison.'}
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              {workspace.candidateCards.map((card) => (
                <div key={card.id}>
                  {(() => {
                    const isApproved = card.id === approvedDirectionId;
                    const isApproving = approvingDirectionId === card.id;

                    return (
                      <div
                        className={cn(
                          'rounded-lg border bg-card/60 p-4',
                          card.isSelected && 'border-emerald-500/40 bg-emerald-500/10',
                          isApproved && 'ring-1 ring-emerald-500/40'
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="text-sm font-semibold">{card.label}</h3>
                              {card.isSelected && (
                                <Badge className="gap-1 border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
                                  <Trophy className="h-3 w-3" />
                                  Leading
                                </Badge>
                              )}
                              {isApproved && (
                                <Badge className="gap-1 border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Approved
                                </Badge>
                              )}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                              {card.sourceModel}
                            </div>
                          </div>
                          {card.rank && (
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-bold">
                              {card.rank}
                            </div>
                          )}
                        </div>

                        {card.summary ? (
                          <p className="mt-3 text-sm text-foreground/85">{card.summary}</p>
                        ) : (
                          <p className="mt-3 text-sm text-muted-foreground">No summary captured for this variant.</p>
                        )}

                        <div className="mt-4 flex flex-wrap gap-2">
                          <Badge variant="outline">Avg rank {formatDesignStudioScore(card.averageRank)}</Badge>
                          <Badge variant="outline">Score {formatDesignStudioScore(card.overallScore)}/5</Badge>
                          {card.rankingsCount !== null && (
                            <Badge variant="outline">{card.rankingsCount} evaluations</Badge>
                          )}
                          {card.totalWeight !== null && (
                            <Badge variant="outline">Weight {formatDesignStudioScore(card.totalWeight)}</Badge>
                          )}
                        </div>

                        {card.criteria.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {card.criteria.slice(0, 4).map((criterion, index) => {
                              const criterionLabel = criterion.label || criterion.key || 'Criterion';
                              return (
                                <div
                                  key={`${card.id}-${criterionLabel}-${index}`}
                                  className={cn(
                                    'rounded-full border px-2.5 py-1 text-xs font-medium',
                                    rubricToneClass(criterion.average_score)
                                  )}
                                >
                                  {criterionLabel} {formatDesignStudioScore(criterion.average_score)}
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {canApprove && (
                          <div className="mt-4">
                            <Button
                              type="button"
                              variant={isApproved ? 'secondary' : 'outline'}
                              size="sm"
                              onClick={() => handleApprove(card.id)}
                              disabled={isApproved || Boolean(approvingDirectionId)}
                            >
                              <CheckCircle2 className={cn('mr-1 h-3.5 w-3.5', isApproving && 'animate-pulse')} />
                              {isApproved ? 'Approved for Refinement' : isApproving ? 'Approving...' : 'Approve Direction'}
                            </Button>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
});

DesignStudioWorkspacePanel.displayName = 'DesignStudioWorkspacePanel';

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

const buildRubricHotspots = (aggregateRubrics) => (
  (Array.isArray(aggregateRubrics) ? aggregateRubrics : [])
    .flatMap((entry) => (
      Array.isArray(entry?.criteria)
        ? entry.criteria.map((criterion) => ({
          model: entry.model,
          label: criterion.label,
          averageScore: criterion.average_score,
          spread: criterion.spread,
        }))
        : []
    ))
    .filter((item) => typeof item.spread === 'number' && item.spread > 0)
    .sort((left, right) => right.spread - left.spread || left.averageScore - right.averageScore)
    .slice(0, 5)
);

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

const CouncilMessageBlock = ({
  message,
  messageIndex,
  onRetryFailedModels,
  onApproveDesignDirection,
  conversationSessionConfig,
}) => {
  const { stage1, stage2, stage3, loading, errors, metadata } = message;
  const [activeTab, setActiveTab] = useState('consensus');
  const [isRetryingFailedModels, setIsRetryingFailedModels] = useState(false);
  const [retryingModelIds, setRetryingModelIds] = useState([]);
  const [isRefreshingSynthesis, setIsRefreshingSynthesis] = useState(false);

  const hasStage1 = stage1 && stage1.length > 0;
  const hasStage2 = stage2 && stage2.length > 0;
  const hasStage3 = stage3 && stage3.response;
  const hasComparisonDiff = hasStage1 && stage1.length > 1;

  const aggregateRankings = metadata?.aggregate_rankings || [];
  const aggregateRubrics = Array.isArray(metadata?.aggregate_rubrics)
    ? metadata.aggregate_rubrics
    : EMPTY_LIST;
  const executionReport = metadata?.execution && metadata.execution.mode !== 'disabled'
    ? metadata.execution
    : null;
  const modelWeightProfile = Array.isArray(metadata?.model_weight_profile)
    ? metadata.model_weight_profile
    : [];
  const visualReviewSurface = useMemo(() => buildVisualReviewSurface(metadata), [metadata]);
  const hasVisualReviewTab = visualReviewSurface.shouldShow;
  const hasExecutionTab = Boolean(executionReport);
  const designStudioMetadata = metadata?.session_type === 'design_studio'
    ? metadata?.design_studio
    : null;
  const approvedDirectionId = (
    metadata?.session_config?.approved_direction_id ||
    conversationSessionConfig?.approved_direction_id ||
    null
  );
  const designStudioHandoff = (
    designStudioMetadata?.handoff?.status === 'ready'
  )
    ? designStudioMetadata.handoff
    : null;

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
  const modelSelection = metadata?.model_selection && typeof metadata.model_selection === 'object'
    ? metadata.model_selection
    : null;
  const modelSelectionWarnings = Array.isArray(modelSelection?.warnings)
    ? modelSelection.warnings.filter((warning) => typeof warning === 'string' && warning.trim())
    : EMPTY_LIST;

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

  const failedModelEntries = useMemo(() => {
    const map = new Map();
    combinedErrors.forEach((errorItem) => {
      const normalized = extractRetryModelName(errorItem.model);
      if (!normalized) return;
      if (!map.has(normalized)) {
        map.set(normalized, {
          modelId: normalized,
          label: errorItem.model || normalized,
        });
      }
    });
    return [...map.values()];
  }, [combinedErrors]);
  const failedModelIds = failedModelEntries.map((entry) => entry.modelId);

  const diffData = useMemo(() => buildComparisonDiff(stage1), [stage1]);
  const rubricHotspots = useMemo(() => buildRubricHotspots(aggregateRubrics), [aggregateRubrics]);

  const hasModelMetadata =
    Array.isArray(metadata?.requested_council_models) ||
    Array.isArray(metadata?.effective_council_models) ||
    Array.isArray(metadata?.responded_council_models);

  const canRetryFailedModels = (
    typeof onRetryFailedModels === 'function' &&
    Number.isInteger(messageIndex) &&
    failedModelIds.length > 0
  );
  const hasRetryHistory = Array.isArray(metadata?.stage1_retry_history) && metadata.stage1_retry_history.length > 0;
  const canRefreshSynthesis = (
    typeof onRetryFailedModels === 'function' &&
    Number.isInteger(messageIndex) &&
    hasStage1 &&
    hasRetryHistory
  );

  const handleRetryFailedModels = async () => {
    if (!canRetryFailedModels || isRetryingFailedModels) return;
    setIsRetryingFailedModels(true);
    try {
      await onRetryFailedModels(messageIndex, failedModelIds);
    } catch {
      // Errors are surfaced via global toasts in App.
    } finally {
      setIsRetryingFailedModels(false);
    }
  };

  const handleRetrySingleModel = async (modelId) => {
    if (!canRetryFailedModels || !modelId) return;
    if (isRetryingFailedModels || retryingModelIds.includes(modelId)) return;

    setRetryingModelIds((current) => [...current, modelId]);
    try {
      await onRetryFailedModels(messageIndex, [modelId]);
    } catch {
      // Errors are surfaced via global toasts in App.
    } finally {
      setRetryingModelIds((current) => current.filter((item) => item !== modelId));
    }
  };

  const handleRefreshSynthesis = async () => {
    if (!canRefreshSynthesis || isRefreshingSynthesis) return;
    setIsRefreshingSynthesis(true);
    try {
      await onRetryFailedModels(messageIndex, [], { refreshSynthesis: true });
    } catch {
      // Errors are surfaced via global toasts in App.
    } finally {
      setIsRefreshingSynthesis(false);
    }
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
            {hasVisualReviewTab && (
              <TabsTrigger value="visual" className="gap-2">
                <FileImage className="h-3.5 w-3.5 text-sky-500" />
                {visualReviewSurface.tabLabel}
              </TabsTrigger>
            )}
            {hasExecutionTab && (
              <TabsTrigger value="execution" className="gap-2">
                <Wrench className="h-3.5 w-3.5 text-emerald-600" />
                Execution
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
                  {modelSelectionWarnings.length > 0 && (
                    <div className="mb-4 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-200">
                      <div className="mb-1 flex items-center gap-2 font-semibold">
                        <AlertTriangle className="h-4 w-4" />
                        Model selection warning
                      </div>
                      <ul className="list-disc space-y-1 pl-5">
                        {modelSelectionWarnings.map((warning, idx) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {canRefreshSynthesis && (
                    <div className="mb-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefreshSynthesis}
                        disabled={isRefreshingSynthesis || isRetryingFailedModels}
                      >
                        <RefreshCw className={cn('mr-1 h-3.5 w-3.5', isRefreshingSynthesis && 'animate-spin')} />
                        {isRefreshingSynthesis ? 'Refreshing Synthesis...' : 'Refresh Synthesis'}
                      </Button>
                    </div>
                  )}
                  <DesignStudioWorkspacePanel
                    designStudio={designStudioMetadata}
                    stage1Errors={stage1Errors}
                    approvedDirectionId={approvedDirectionId}
                    onApproveDesignDirection={onApproveDesignDirection}
                  />
                  <DesignStudioHandoffPanel handoff={designStudioHandoff} />
                  <MarkdownContent content={stage3.response} />
                  {loading?.stage3 && <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />}
                </>
              ) : (
                <>
                  <DesignStudioWorkspacePanel
                    designStudio={designStudioMetadata}
                    stage1Errors={stage1Errors}
                    approvedDirectionId={approvedDirectionId}
                    onApproveDesignDirection={onApproveDesignDirection}
                  />
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
                </>
              )}
            </div>
          </TabsContent>

          <TabsContent value="rankings" className="m-0 focus-visible:ring-0">
            <RankingsTabContent
              aggregateRankings={aggregateRankings}
              aggregateRubrics={aggregateRubrics}
              framework={metadata?.framework}
              modelWeightProfile={modelWeightProfile}
            />
          </TabsContent>

          <TabsContent value="visual" className="m-0 focus-visible:ring-0">
            <VisualReviewPanel
              artifacts={visualReviewSurface.imageArtifacts}
              findings={visualReviewSurface.findings}
              title={visualReviewSurface.title}
              description={visualReviewSurface.description}
            />
          </TabsContent>

          <TabsContent value="execution" className="m-0 focus-visible:ring-0">
            <ExecutionTabContent execution={executionReport} />
          </TabsContent>

          <TabsContent value="diff" className="m-0 focus-visible:ring-0">
            <DiffTabContent diffData={diffData} rubricHotspots={rubricHotspots} />
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
              <div className="flex items-center gap-2 flex-wrap">
                {canRetryFailedModels && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 border-destructive/40 text-destructive hover:text-destructive"
                    onClick={handleRetryFailedModels}
                    disabled={isRetryingFailedModels || isRefreshingSynthesis}
                  >
                    <RotateCcw className={cn('mr-1 h-3.5 w-3.5', isRetryingFailedModels && 'animate-spin')} />
                    {isRetryingFailedModels ? 'Retrying...' : 'Retry Failed Models'}
                  </Button>
                )}
              </div>
            </div>
            {failedModelEntries.length > 0 && canRetryFailedModels && (
              <div className="mb-3 flex flex-wrap gap-2">
                {failedModelEntries.map((entry) => {
                  const isRetryingModel = retryingModelIds.includes(entry.modelId);
                  return (
                    <Button
                      key={entry.modelId}
                      variant="outline"
                      size="sm"
                      className="h-7 border-destructive/40 text-destructive hover:text-destructive"
                      onClick={() => handleRetrySingleModel(entry.modelId)}
                      disabled={isRetryingModel || isRetryingFailedModels || isRefreshingSynthesis}
                    >
                      <RotateCcw className={cn('mr-1 h-3.5 w-3.5', isRetryingModel && 'animate-spin')} />
                      {isRetryingModel ? 'Retrying...' : `Retry ${entry.label}`}
                    </Button>
                  );
                })}
              </div>
            )}
            <ul className="list-disc list-inside space-y-1">
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
