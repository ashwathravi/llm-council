const EMPTY_LIST = [];

const asArray = (value) => (Array.isArray(value) ? value : EMPTY_LIST);

const cleanString = (value, fallback = '') => (
  typeof value === 'string' && value.trim() ? value.trim() : fallback
);

const toMapByDirection = (items) => {
  const map = new Map();
  asArray(items).forEach((item) => {
    const directionId = cleanString(item?.direction_id);
    if (directionId) {
      map.set(directionId, item);
    }
  });
  return map;
};

export const formatDesignStudioScore = (value) => (
  typeof value === 'number' && Number.isFinite(value)
    ? value.toFixed(1).replace(/\.0$/, '')
    : 'n/a'
);

export const buildDesignStudioWorkspaceView = (designStudio = {}, stage1Errors = []) => {
  const candidates = asArray(designStudio?.candidate_directions)
    .filter((candidate) => candidate && typeof candidate === 'object');
  const comparison = designStudio?.comparison && typeof designStudio.comparison === 'object'
    ? designStudio.comparison
    : {};
  const rankedDirections = asArray(comparison.ranked_directions);
  const rubricSummaries = asArray(comparison.rubric_summaries);
  const rankingByDirection = toMapByDirection(rankedDirections);
  const rubricByDirection = toMapByDirection(rubricSummaries);
  const firstRankedDirectionId = cleanString(rankedDirections[0]?.direction_id);
  const firstCandidateId = cleanString(candidates[0]?.id);
  const selectedDirectionId = cleanString(
    designStudio?.selected_direction_id,
    firstRankedDirectionId || firstCandidateId
  );

  const failedVariants = asArray(stage1Errors)
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      model: cleanString(item.model, 'Unknown model'),
      error: cleanString(item.error, 'Unknown error'),
    }));

  const candidateCards = candidates
    .map((candidate, index) => {
      const id = cleanString(candidate.id, `direction-${index + 1}`);
      const ranking = rankingByDirection.get(id) || {};
      const rubric = rubricByDirection.get(id) || {};
      const criteria = asArray(rubric.criteria)
        .filter((criterion) => criterion && typeof criterion === 'object');

      return {
        id,
        label: cleanString(candidate.label, `Direction ${index + 1}`),
        responseLabel: cleanString(candidate.response_label),
        sourceModel: cleanString(candidate.source_model, 'Unknown model'),
        summary: cleanString(candidate.summary),
        rank: typeof ranking.rank === 'number' ? ranking.rank : null,
        averageRank: typeof ranking.average_rank === 'number' ? ranking.average_rank : null,
        rankingsCount: typeof ranking.rankings_count === 'number' ? ranking.rankings_count : null,
        totalWeight: typeof ranking.total_weight === 'number' ? ranking.total_weight : null,
        weighted: Boolean(ranking.weighted),
        overallScore: typeof rubric.overall_score === 'number' ? rubric.overall_score : null,
        criteria,
        isSelected: id === selectedDirectionId,
        originalIndex: index,
      };
    })
    .sort((left, right) => (
      (left.rank ?? Number.POSITIVE_INFINITY) - (right.rank ?? Number.POSITIVE_INFINITY) ||
      left.originalIndex - right.originalIndex
    ));

  const comparisonStatus = cleanString(comparison.status, 'pending');
  const status = candidateCards.length === 0
    ? 'empty'
    : candidateCards.length === 1
      ? 'single'
      : comparisonStatus === 'complete'
        ? 'complete'
        : 'pending';

  return {
    status,
    comparisonStatus,
    candidateCards,
    failedVariants,
    selectedDirectionId,
    selectedCard: candidateCards.find((card) => card.isSelected) || candidateCards[0] || null,
    hasPartialFailures: failedVariants.length > 0,
    hasComparison: candidateCards.length > 1,
  };
};
