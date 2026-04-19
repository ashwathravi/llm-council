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

export const getSessionTypeLabel = (sessionType) =>
  SESSION_TYPE_LABELS[sessionType] || SESSION_TYPE_LABELS.general;

export const getPrimaryArtifactCount = (primaryArtifacts) =>
  Array.isArray(primaryArtifacts) ? primaryArtifacts.length : 0;
