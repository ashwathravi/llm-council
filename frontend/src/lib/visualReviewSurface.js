const EMPTY_LIST = [];

const asArray = (value) => (Array.isArray(value) ? value : EMPTY_LIST);

const isStructuredFinding = (finding) => (
  Boolean(
    finding?.artifact_id &&
    typeof finding?.title === 'string' &&
    typeof finding?.comment === 'string'
  )
);

export const buildVisualReviewSurface = (metadata = {}) => {
  const imageArtifacts = asArray(metadata?.primary_artifacts)
    .filter((artifact) => artifact?.kind === 'image' && artifact?.preview_url);
  const findings = asArray(metadata?.visual_findings).filter(isStructuredFinding);
  const surfaceMetadata = metadata?.visual_review && typeof metadata.visual_review === 'object'
    ? metadata.visual_review
    : {};
  const sessionType = metadata?.session_type;
  const isVisualReviewSession = sessionType === 'visual_review';
  const isDesignStudioSession = sessionType === 'design_studio';
  const metadataEnabled = surfaceMetadata.panel_enabled === true || surfaceMetadata.enabled === true;
  const shouldShow = imageArtifacts.length > 0 && (
    isVisualReviewSession ||
    (findings.length > 0 && (metadataEnabled || isDesignStudioSession))
  );
  const mode = surfaceMetadata.mode || (
    isDesignStudioSession ? 'design_studio_critique' : 'visual_review'
  );

  return {
    shouldShow,
    imageArtifacts,
    findings,
    mode,
    tabLabel: surfaceMetadata.tab_label || (mode === 'design_studio_critique' ? 'Critique' : 'Visual'),
    title: surfaceMetadata.title || (
      mode === 'design_studio_critique' ? 'Artifact Critique Surface' : undefined
    ),
    description: surfaceMetadata.description || (
      mode === 'design_studio_critique'
        ? 'Inspect artifact-tied critique findings without leaving the Design Studio flow.'
        : undefined
    ),
  };
};
