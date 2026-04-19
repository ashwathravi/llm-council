import { useMemo, useState } from 'react';
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from '../api';

const SEVERITY_STYLES = {
  low: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  medium: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  high: 'border-destructive/30 bg-destructive/10 text-destructive',
};

function severityClass(severity) {
  return SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium;
}

export default function VisualReviewPanel({ artifacts = [], findings = [] }) {
  const imageArtifacts = useMemo(
    () => (Array.isArray(artifacts) ? artifacts : []).filter((artifact) =>
      artifact?.kind === 'image' && artifact?.preview_url
    ),
    [artifacts]
  );
  const structuredFindings = useMemo(
    () => (Array.isArray(findings) ? findings : []).filter((finding) =>
      finding?.artifact_id && typeof finding?.title === 'string' && typeof finding?.comment === 'string'
    ),
    [findings]
  );
  const [manualActiveFindingId, setManualActiveFindingId] = useState(null);
  const activeFindingId = structuredFindings.some((finding) => finding.id === manualActiveFindingId)
    ? manualActiveFindingId
    : structuredFindings[0]?.id || null;

  const findingsByArtifact = useMemo(() => {
    const bucket = new Map();
    structuredFindings.forEach((finding) => {
      const list = bucket.get(finding.artifact_id) || [];
      list.push(finding);
      bucket.set(finding.artifact_id, list);
    });
    return bucket;
  }, [structuredFindings]);

  const hasComparison = imageArtifacts.length > 1;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h3 className="font-semibold">
            {hasComparison ? 'Side-by-Side Comparison' : 'Visual Review Surface'}
          </h3>
          <p className="text-sm text-muted-foreground">
            {hasComparison
              ? 'Review both artifacts together and inspect region-tied findings directly on the images.'
              : 'Inspect the uploaded artifact and jump through structured visual findings.'}
          </p>
        </div>
        <Badge variant="outline">{structuredFindings.length} findings</Badge>
      </div>

      {imageArtifacts.length > 0 ? (
        <div className={cn('grid gap-4', hasComparison ? 'lg:grid-cols-2' : 'grid-cols-1')}>
          {imageArtifacts.map((artifact) => {
            const artifactFindings = findingsByArtifact.get(artifact.id) || [];

            return (
              <div key={artifact.id} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{artifact.label || artifact.filename || 'Image artifact'}</div>
                    <div className="text-xs text-muted-foreground">
                      {artifactFindings.length} hotspots
                    </div>
                  </div>
                  {artifactFindings.length > 0 && (
                    <Badge variant="secondary">{artifactFindings.length}</Badge>
                  )}
                </div>

                <div className="relative overflow-hidden rounded-xl border bg-muted/20">
                  <img
                    src={api.resolveUrl(artifact.preview_url)}
                    alt={artifact.label || artifact.filename || 'Visual artifact'}
                    className="block w-full object-contain"
                  />

                  {artifactFindings.map((finding, index) => {
                    const isActive = finding.id === activeFindingId;

                    return (
                      <button
                        key={finding.id}
                        type="button"
                        onClick={() => setManualActiveFindingId(finding.id)}
                        className={cn(
                          'absolute rounded-lg border-2 transition-all',
                          isActive
                            ? 'border-primary bg-primary/10 ring-2 ring-primary/30'
                            : 'border-white/70 bg-black/10 hover:border-primary/70'
                        )}
                        style={{
                          left: `${finding.x}%`,
                          top: `${finding.y}%`,
                          width: `${finding.w}%`,
                          height: `${finding.h}%`,
                        }}
                        aria-label={`Focus finding ${index + 1}: ${finding.title}`}
                      >
                        <span className="absolute left-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-background/90 text-[11px] font-semibold text-foreground shadow">
                          {index + 1}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
          No visual artifacts are attached to this message.
        </div>
      )}

      <div className="space-y-2">
        <h4 className="font-semibold">Structured Findings</h4>
        {structuredFindings.length > 0 ? (
          <div className="space-y-2">
            {structuredFindings.map((finding, index) => {
              const isActive = finding.id === activeFindingId;
              return (
                <button
                  key={finding.id}
                  type="button"
                  onClick={() => setManualActiveFindingId(finding.id)}
                  className={cn(
                    'w-full rounded-lg border p-3 text-left transition-colors',
                    isActive ? 'border-primary bg-primary/5' : 'bg-card/40 hover:bg-card/70'
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{index + 1}. {finding.title}</div>
                      <div className="text-xs text-muted-foreground">{finding.artifact_label}</div>
                    </div>
                    <Badge variant="outline" className={severityClass(finding.severity)}>
                      {finding.severity}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm text-foreground/90">{finding.comment}</p>
                </button>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No structured visual findings were extracted from this review yet.
          </p>
        )}
      </div>
    </div>
  );
}
