export const SESSION_TYPE_OPTIONS = [
  {
    id: 'general',
    name: 'General',
    description: 'Open-ended council sessions for mixed questions or artifact-light work.',
  },
  {
    id: 'visual_review',
    name: 'Visual Review',
    description: 'Sessions centered on screenshots, mockups, and design critique.',
  },
  {
    id: 'code_review',
    name: 'Code Review',
    description: 'Sessions focused on repos, diffs, implementation quality, and risks.',
  },
  {
    id: 'build_spec',
    name: 'Build/Spec',
    description: 'Sessions for specs, briefs, execution plans, and implementation handoffs.',
  },
  {
    id: 'research_docs',
    name: 'Research/Docs',
    description: 'Sessions that synthesize notes, reports, and supporting source material.',
  },
];

export const SESSION_TYPE_LABELS = Object.fromEntries(
  SESSION_TYPE_OPTIONS.map((option) => [option.id, option.name])
);

export const SESSION_TYPE_PLACEHOLDERS = {
  general: 'Message the Council...',
  visual_review: 'Ask for a visual or UX critique...',
  code_review: 'Paste a diff, repo slice, or ask for a code review...',
  build_spec: 'Ask the Council to plan, scope, or implement against a spec...',
  research_docs: 'Ask a question grounded in your attached source material...',
};

export const EXECUTION_MODE_OPTIONS = [
  {
    id: 'disabled',
    name: 'Disabled',
    description: 'Standard code review only. No candidate patch or checks are attempted.',
  },
  {
    id: 'safe_patch_checks',
    name: 'Safe Patch + Checks',
    description: 'Generate a candidate diff in a temp workspace and run guarded auto-detected checks.',
  },
];

export const EXECUTION_MODE_LABELS = Object.fromEntries(
  EXECUTION_MODE_OPTIONS.map((option) => [option.id, option.name])
);

export const getSessionTypeLabel = (sessionType) =>
  SESSION_TYPE_LABELS[sessionType] || SESSION_TYPE_LABELS.general;

export const getExecutionModeLabel = (executionMode) =>
  EXECUTION_MODE_LABELS[executionMode] || EXECUTION_MODE_LABELS.disabled;

export const getPrimaryArtifactCount = (primaryArtifacts) =>
  Array.isArray(primaryArtifacts) ? primaryArtifacts.length : 0;
