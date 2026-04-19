export const SPECIALIST_TEMPLATES = [
  {
    id: 'visual_ux_review',
    sessionType: 'visual_review',
    name: 'UX Review Council',
    description: 'Usability, hierarchy, accessibility, and product clarity.',
    defaultFramework: 'standard',
  },
  {
    id: 'visual_accessibility_review',
    sessionType: 'visual_review',
    name: 'Accessibility Review Council',
    description: 'Contrast, focus states, legibility, and interaction safety.',
    defaultFramework: 'standard',
  },
  {
    id: 'visual_pm_review',
    sessionType: 'visual_review',
    name: 'PM Readout Council',
    description: 'Product intent, CTA strength, and user-value communication.',
    defaultFramework: 'ensemble',
  },
  {
    id: 'code_senior_review',
    sessionType: 'code_review',
    name: 'Senior Engineer Council',
    description: 'Correctness, regression risk, maintainability, and tests.',
    defaultFramework: 'standard',
  },
  {
    id: 'code_security_review',
    sessionType: 'code_review',
    name: 'Security Review Council',
    description: 'Trust boundaries, unsafe defaults, and exploitability.',
    defaultFramework: 'standard',
  },
  {
    id: 'code_performance_review',
    sessionType: 'code_review',
    name: 'Performance Review Council',
    description: 'Hot paths, wasteful work, and scalability concerns.',
    defaultFramework: 'debate',
  },
  {
    id: 'code_architecture_review',
    sessionType: 'code_review',
    name: 'Architecture Review Council',
    description: 'Layering, module boundaries, and long-term structure.',
    defaultFramework: 'heterogeneous',
  },
];

export const getTemplatesForSessionType = (sessionType) =>
  SPECIALIST_TEMPLATES.filter((template) => template.sessionType === sessionType);

export const getSpecialistTemplate = (templateId) =>
  SPECIALIST_TEMPLATES.find((template) => template.id === templateId) || null;

export const getSpecialistTemplateLabel = (templateId) =>
  getSpecialistTemplate(templateId)?.name || null;
