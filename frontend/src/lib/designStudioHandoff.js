export const DESIGN_HANDOFF_KEYS = [
  'rationale',
  'component_map',
  'handoff_notes',
  'state_notes',
  'platform_constraints',
  'open_questions',
];

const EMPTY_LIST = [];

export const getDesignStudioHandoffSection = (handoff, key) => {
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

export const hasDesignStudioHandoffSectionContent = (section) => (
  Boolean(section && (section.content.trim() || section.items.length > 0))
);

export const buildDesignStudioHandoffView = (handoff) => {
  if (!handoff || handoff.status !== 'ready') {
    return {
      selectedRef: null,
      selectedSection: null,
      sections: EMPTY_LIST,
      hasContent: false,
    };
  }

  const selectedRef = handoff.selected_direction_ref && typeof handoff.selected_direction_ref === 'object'
    ? handoff.selected_direction_ref
    : null;
  const selectedSection = getDesignStudioHandoffSection(handoff, 'selected_direction');
  const sections = DESIGN_HANDOFF_KEYS
    .map((key) => getDesignStudioHandoffSection(handoff, key))
    .filter(hasDesignStudioHandoffSectionContent);

  return {
    selectedRef,
    selectedSection,
    sections,
    hasContent: Boolean(
      selectedRef ||
      hasDesignStudioHandoffSectionContent(selectedSection) ||
      sections.length > 0
    ),
  };
};
