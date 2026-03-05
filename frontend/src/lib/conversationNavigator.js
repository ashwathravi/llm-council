export const TURN_ANCHOR_PREFIX = 'turn-anchor-';
export const NAVIGATOR_SNIPPET_MAX_LENGTH = 100;

export const buildTurnAnchorId = (messageIndex) => `${TURN_ANCHOR_PREFIX}${messageIndex}`;

const normalizeText = (value) => String(value || '').replace(/\s+/g, ' ').trim();

export const buildSnippet = (value, maxLength = NAVIGATOR_SNIPPET_MAX_LENGTH) => {
  const normalized = normalizeText(value);
  if (!normalized) return '(No text)';
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength).trimEnd()}...`;
};

const getAssistantErrorCount = (assistantMessage) => {
  if (!assistantMessage || typeof assistantMessage !== 'object') return 0;
  const directErrors = Array.isArray(assistantMessage.errors) ? assistantMessage.errors.length : 0;
  const stage1Errors = Array.isArray(assistantMessage?.metadata?.stage1_errors)
    ? assistantMessage.metadata.stage1_errors.length
    : 0;
  return directErrors + stage1Errors;
};

export const getTurnStatus = (assistantMessage, isLatestTurnLoading = false) => {
  if (!assistantMessage || assistantMessage.role !== 'assistant') {
    return isLatestTurnLoading ? 'in_progress' : 'complete';
  }

  const loading = assistantMessage.loading;
  const isLoading = Boolean(
    loading?.stage1 ||
    loading?.stage2 ||
    loading?.stage3
  );
  if (isLoading) return 'in_progress';

  if (getAssistantErrorCount(assistantMessage) > 0) {
    return 'has_errors';
  }

  const stage3Response = assistantMessage?.stage3?.response;
  if (typeof stage3Response === 'string' && stage3Response.trim()) {
    return 'complete';
  }

  return 'in_progress';
};

export const NAVIGATOR_STATUS_META = {
  in_progress: {
    label: 'In progress',
    className: 'bg-amber-500/15 text-amber-700 border-amber-500/40',
  },
  has_errors: {
    label: 'Has errors',
    className: 'bg-destructive/15 text-destructive border-destructive/40',
  },
  complete: {
    label: 'Complete',
    className: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/40',
  },
};

export const buildConversationOutline = (messages = [], isConversationLoading = false) => {
  if (!Array.isArray(messages) || messages.length === 0) return [];

  const userIndices = [];
  messages.forEach((message, index) => {
    if (message?.role === 'user') {
      userIndices.push(index);
    }
  });

  return userIndices.map((messageIndex, turnPosition) => {
    const userMessage = messages[messageIndex] || {};
    const nextMessage = messages[messageIndex + 1];
    const assistantMessage = nextMessage?.role === 'assistant' ? nextMessage : null;
    const isLastTurn = turnPosition === userIndices.length - 1;
    const status = getTurnStatus(assistantMessage, isLastTurn && isConversationLoading);

    return {
      turnNumber: turnPosition + 1,
      messageIndex,
      anchorId: buildTurnAnchorId(messageIndex),
      snippet: buildSnippet(userMessage.content),
      status,
    };
  });
};
