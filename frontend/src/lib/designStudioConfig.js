export const DESIGN_TARGET_OPTIONS = [
  {
    id: 'web_app',
    name: 'Web App',
    description: 'Browser-first product design directions.',
  },
  {
    id: 'ios_app',
    name: 'iOS App',
    description: 'Native iPhone and iPad design directions.',
  },
  {
    id: 'mixed',
    name: 'Mixed Web + iOS',
    description: 'Cross-platform direction with shared intent.',
  },
];

export const STUDIO_GOAL_OPTIONS = [
  {
    id: 'generate',
    name: 'Generate',
    description: 'Explore fresh directions from a brief.',
  },
  {
    id: 'iterate',
    name: 'Iterate',
    description: 'Refine an existing direction.',
  },
  {
    id: 'compare',
    name: 'Compare',
    description: 'Stack options against each other.',
  },
  {
    id: 'review',
    name: 'Review',
    description: 'Pressure-test a proposed direction.',
  },
  {
    id: 'handoff',
    name: 'Handoff',
    description: 'Turn a direction into build notes.',
  },
];

export const DESIGN_TARGET_LABELS = Object.fromEntries(
  DESIGN_TARGET_OPTIONS.map((option) => [option.id, option.name])
);

export const STUDIO_GOAL_LABELS = Object.fromEntries(
  STUDIO_GOAL_OPTIONS.map((option) => [option.id, option.name])
);

export const DEFAULT_DESIGN_STUDIO_CONFIG = {
  design_target: 'web_app',
  studio_goal: 'generate',
  approved_direction_id: null,
};

export const getStudioGoalLabel = (value) =>
  STUDIO_GOAL_LABELS[value] || STUDIO_GOAL_LABELS[DEFAULT_DESIGN_STUDIO_CONFIG.studio_goal];

const normalizeDesignTarget = (value) => {
  if (typeof value !== 'string') {
    return DEFAULT_DESIGN_STUDIO_CONFIG.design_target;
  }

  const normalized = value.trim().toLowerCase().replace(/[-\s]+/g, '_');
  if (normalized === 'both') {
    return 'mixed';
  }
  return DESIGN_TARGET_LABELS[normalized]
    ? normalized
    : DEFAULT_DESIGN_STUDIO_CONFIG.design_target;
};

export const getDesignTargetLabel = (value) =>
  DESIGN_TARGET_LABELS[normalizeDesignTarget(value)];

export const normalizeSessionConfig = (sessionType, sessionConfig = {}) => {
  if (sessionType !== 'design_studio') {
    return {};
  }

  const next = sessionConfig && typeof sessionConfig === 'object' ? sessionConfig : {};
  const approvedDirectionId = typeof next.approved_direction_id === 'string' && next.approved_direction_id.trim()
    ? next.approved_direction_id.trim()
    : null;

  return {
    design_target: normalizeDesignTarget(next.design_target),
    studio_goal: STUDIO_GOAL_LABELS[next.studio_goal]
      ? next.studio_goal
      : DEFAULT_DESIGN_STUDIO_CONFIG.studio_goal,
    approved_direction_id: approvedDirectionId,
  };
};
